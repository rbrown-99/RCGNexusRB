"""Cosmos DB persistence for purchase orders, sessions, and optimization runs.

Uses managed identity (DefaultAzureCredential) when COSMOS_ENDPOINT is set.
If not set (local dev without Cosmos), all persistence calls become no-ops.

Containers (created by Bicep):
  - purchase_orders   pk=/store_code     one doc per order line
  - optimization_runs pk=/session_id     one doc per optimize/reoptimize call
  - sessions          pk=/session_id     session metadata (orders/locations/bundle counts)
"""
from __future__ import annotations

import datetime as _dt
import logging
import threading
from typing import Any, Iterable

from .config import settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_client = None
_db = None
_containers: dict[str, Any] = {}

CN_POS = "purchase_orders"
CN_RUNS = "optimization_runs"
CN_SESSIONS = "sessions"


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def enabled() -> bool:
    return bool(settings.cosmos_endpoint)


def _ensure_client() -> bool:
    """Lazily build the Cosmos client. Returns True if persistence is available."""
    global _client, _db
    if not enabled():
        return False
    if _client is not None:
        return True
    with _lock:
        if _client is not None:
            return True
        try:
            from azure.cosmos import CosmosClient  # type: ignore
            from azure.identity import DefaultAzureCredential  # type: ignore

            cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
            _client = CosmosClient(settings.cosmos_endpoint, credential=cred)
            _db = _client.get_database_client(settings.cosmos_database)
            for cn in (CN_POS, CN_RUNS, CN_SESSIONS):
                _containers[cn] = _db.get_container_client(cn)
            log.info("cosmos: connected to %s/%s", settings.cosmos_endpoint, settings.cosmos_database)
            return True
        except Exception as e:  # pragma: no cover — best-effort
            log.warning("cosmos: failed to initialize, persistence disabled: %s", e)
            _client = None
            _db = None
            _containers.clear()
            return False


def _safe_upsert(container_name: str, doc: dict) -> None:
    if not _ensure_client():
        return
    try:
        _containers[container_name].upsert_item(doc)
    except Exception as e:  # pragma: no cover
        log.warning("cosmos: upsert into %s failed: %s", container_name, e)


# ---------------- public helpers ----------------

def save_purchase_orders(session_id: str, orders: Iterable[Any]) -> int:
    """Persist parsed purchase orders. Returns the count saved."""
    if not _ensure_client():
        return 0
    n = 0
    now = _now_iso()
    for o in orders:
        d = o.model_dump() if hasattr(o, "model_dump") else dict(o)
        store_code = str(d.get("store_code") or d.get("location_code") or "UNKNOWN")
        order_id = str(d.get("order_id") or d.get("id") or f"{session_id}-{n:04d}")
        doc = {
            "id": f"{session_id}:{order_id}",
            "store_code": store_code,
            "session_id": session_id,
            "order_id": order_id,
            "order": d,
            "created_at": now,
        }
        _safe_upsert(CN_POS, doc)
        n += 1
    return n


def save_session(
    session_id: str,
    *,
    n_orders: int,
    n_locations: int,
    n_constraints: int,
    source: str,
) -> None:
    doc = {
        "id": session_id,
        "session_id": session_id,
        "source": source,  # "upload" or "samples"
        "n_orders": n_orders,
        "n_locations": n_locations,
        "n_constraints": n_constraints,
        "created_at": _now_iso(),
    }
    _safe_upsert(CN_SESSIONS, doc)


def save_optimization_run(
    session_id: str,
    *,
    kind: str,
    result: Any,
    distance_source: str | None = None,
    notes: str | None = None,
) -> None:
    """Persist a full optimization result. `kind` is 'optimize' | 'reoptimize'."""
    payload = result.model_dump() if hasattr(result, "model_dump") else result
    run_id = f"{session_id}:{_now_iso()}"
    doc = {
        "id": run_id,
        "session_id": session_id,
        "kind": kind,
        "distance_source": distance_source,
        "notes": notes,
        "result": payload,
        "created_at": _now_iso(),
    }
    _safe_upsert(CN_RUNS, doc)


def list_purchase_orders(store_code: str | None = None, max_items: int = 100) -> list[dict]:
    if not _ensure_client():
        return []
    try:
        if store_code:
            items = _containers[CN_POS].query_items(
                query="SELECT TOP @n * FROM c WHERE c.store_code = @sc ORDER BY c.created_at DESC",
                parameters=[{"name": "@n", "value": max_items}, {"name": "@sc", "value": store_code}],
                partition_key=store_code,
            )
        else:
            items = _containers[CN_POS].query_items(
                query="SELECT TOP @n * FROM c ORDER BY c.created_at DESC",
                parameters=[{"name": "@n", "value": max_items}],
                enable_cross_partition_query=True,
            )
        return list(items)
    except Exception as e:  # pragma: no cover
        log.warning("cosmos: list_purchase_orders failed: %s", e)
        return []


def get_latest_run(session_id: str) -> dict | None:
    if not _ensure_client():
        return None
    try:
        items = list(_containers[CN_RUNS].query_items(
            query="SELECT TOP 1 * FROM c WHERE c.session_id = @sid ORDER BY c.created_at DESC",
            parameters=[{"name": "@sid", "value": session_id}],
            partition_key=session_id,
        ))
        return items[0] if items else None
    except Exception as e:  # pragma: no cover
        log.warning("cosmos: get_latest_run failed: %s", e)
        return None
