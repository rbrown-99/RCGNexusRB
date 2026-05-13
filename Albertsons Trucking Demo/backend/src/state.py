"""Shared in-memory store for optimization sessions.

POC only — single-process state. Production would use Redis/DB.
"""
from __future__ import annotations

import uuid
from threading import Lock
from typing import Any

from ..models import ConstraintBundle, Location, OptimizationResult, Order


class _Store:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sessions: dict[str, dict[str, Any]] = {}

    def create(
        self,
        orders: list[Order],
        locations: list[Location],
        bundle: ConstraintBundle,
        result: OptimizationResult | None = None,
    ) -> str:
        sid = uuid.uuid4().hex[:12]
        with self._lock:
            self._sessions[sid] = {
                "orders": orders,
                "locations": locations,
                "bundle": bundle,
                "result": result,
            }
        return sid

    def get(self, sid: str) -> dict[str, Any]:
        with self._lock:
            if sid not in self._sessions:
                raise KeyError(sid)
            return self._sessions[sid]

    def update_result(self, sid: str, result: OptimizationResult) -> None:
        with self._lock:
            self._sessions[sid]["result"] = result

    def list(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())


store = _Store()
