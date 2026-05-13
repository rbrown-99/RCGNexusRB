"""MCP server for the Albertsons truck-routing backend.

Exposes the routing API as MCP tools that a Foundry agent (or any MCP client)
can call. Uses the Streamable HTTP transport on port 8080 at /mcp.

Tools:
  - optimize_from_samples       run VRP on bundled sample data
  - optimize                    run VRP on an existing session_id
  - reoptimize                  re-run with constraint overrides
  - validate                    re-run rule checks on a session
  - explain                     get rationale for a single route
  - compare                     compare reoptimize vs baseline
  - list_purchase_orders        list POs from Cosmos (optionally by store_code)
  - get_optimization_run        fetch the latest run from Cosmos by session_id
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("albrouting-mcp")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000").rstrip("/")
COSMOS_ENDPOINT = os.environ.get("COSMOS_ENDPOINT") or None
COSMOS_DATABASE = os.environ.get("COSMOS_DATABASE", "routing")

# ---------- backend HTTP client ----------
_http = httpx.AsyncClient(timeout=120.0)


async def _post(path: str, **kw) -> dict:
    r = await _http.post(f"{BACKEND_URL}{path}", **kw)
    r.raise_for_status()
    return r.json()


async def _get(path: str, **kw) -> dict:
    r = await _http.get(f"{BACKEND_URL}{path}", **kw)
    r.raise_for_status()
    return r.json()


# ---------- optional Cosmos read-only helpers ----------
_cosmos_clients: dict[str, Any] = {}


def _cosmos_container(name: str):
    if not COSMOS_ENDPOINT:
        return None
    if name in _cosmos_clients:
        return _cosmos_clients[name]
    try:
        from azure.cosmos import CosmosClient  # type: ignore
        from azure.identity import DefaultAzureCredential  # type: ignore

        cred = DefaultAzureCredential(exclude_interactive_browser_credential=True)
        client = CosmosClient(COSMOS_ENDPOINT, credential=cred)
        db = client.get_database_client(COSMOS_DATABASE)
        c = db.get_container_client(name)
        _cosmos_clients[name] = c
        return c
    except Exception as e:
        log.warning("cosmos init failed: %s", e)
        return None


# ---------- MCP server ----------
from mcp.server.fastmcp import FastMCP  # type: ignore

mcp = FastMCP("albertsons-routing", host="0.0.0.0", port=8080)


@mcp.tool()
async def optimize_from_samples() -> dict:
    """Run the VRP optimizer on the bundled sample dataset (100 orders / 30 stores).

    Returns a session_id, full route plan, KPIs, exceptions, and which distance
    source was used (Azure Maps vs haversine fallback).
    """
    return await _post("/api/optimize-from-samples")


@mcp.tool()
async def optimize(session_id: str) -> dict:
    """Re-run the optimizer on an existing session_id (no constraint changes)."""
    data = {"session_id": session_id}
    r = await _http.post(f"{BACKEND_URL}/api/optimize", data=data)
    r.raise_for_status()
    return r.json()


@mcp.tool()
async def reoptimize(
    session_id: str,
    remove_trailer_configs: list[str] | None = None,
    remove_locations: list[str] | None = None,
    remove_orders: list[str] | None = None,
    notes: str | None = None,
) -> dict:
    """Re-run the optimizer with constraint overrides (drop trailers, drop stores, drop orders)."""
    body: dict[str, Any] = {}
    if remove_trailer_configs: body["remove_trailer_configs"] = remove_trailer_configs
    if remove_locations:       body["remove_locations"] = remove_locations
    if remove_orders:          body["remove_orders"] = remove_orders
    if notes:                  body["notes"] = notes
    return await _post(f"/api/reoptimize/{session_id}", json=body)


@mcp.tool()
async def validate(session_id: str) -> dict:
    """Re-run all rule checks (cube/weight/HOS/windows/road) on the current plan."""
    return await _post(f"/api/validate/{session_id}")


@mcp.tool()
async def explain(session_id: str, route_id: str) -> dict:
    """Get a human-readable rationale for a specific route."""
    return await _get(f"/api/explain/{session_id}/{route_id}")


@mcp.tool()
async def compare(session_id: str) -> dict:
    """Compare the latest reoptimize vs the baseline for the session."""
    return await _post(f"/api/compare/{session_id}")


@mcp.tool()
async def list_purchase_orders(store_code: str | None = None, max_items: int = 50) -> dict:
    """List recent purchase orders from Cosmos. Optionally filter by store_code."""
    c = _cosmos_container("purchase_orders")
    if c is None:
        return {"items": [], "note": "cosmos not configured for this MCP server"}
    try:
        if store_code:
            items = list(c.query_items(
                query="SELECT TOP @n * FROM c WHERE c.store_code = @sc ORDER BY c.created_at DESC",
                parameters=[{"name": "@n", "value": int(max_items)}, {"name": "@sc", "value": store_code}],
                partition_key=store_code,
            ))
        else:
            items = list(c.query_items(
                query="SELECT TOP @n * FROM c ORDER BY c.created_at DESC",
                parameters=[{"name": "@n", "value": int(max_items)}],
                enable_cross_partition_query=True,
            ))
        return {"items": items, "count": len(items)}
    except Exception as e:
        return {"items": [], "error": str(e)}


@mcp.tool()
async def get_optimization_run(session_id: str) -> dict:
    """Fetch the latest persisted optimization run for a session_id from Cosmos."""
    c = _cosmos_container("optimization_runs")
    if c is None:
        return {"run": None, "note": "cosmos not configured for this MCP server"}
    try:
        items = list(c.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.session_id = @sid ORDER BY c.created_at DESC",
            parameters=[{"name": "@sid", "value": session_id}],
            partition_key=session_id,
        ))
        return {"run": items[0] if items else None}
    except Exception as e:
        return {"run": None, "error": str(e)}


if __name__ == "__main__":
    log.info("starting MCP server backend=%s cosmos=%s", BACKEND_URL, bool(COSMOS_ENDPOINT))
    # Streamable HTTP transport (preferred for hosted MCP servers).
    # FastMCP exposes /mcp endpoint for the streamable-http transport.
    mcp.run(transport="streamable-http")
