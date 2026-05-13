"""POST /api/compare — diff two optimization results."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..state import store

router = APIRouter(prefix="/api", tags=["compare"])


@router.post("/compare")
async def compare(session_a: str, session_b: str):
    try:
        a = store.get(session_a)["result"]
        b = store.get(session_b)["result"]
    except KeyError as e:
        raise HTTPException(404, f"unknown session {e}")
    if not (a and b):
        raise HTTPException(400, "both sessions need a result")

    return {
        "session_a": session_a,
        "session_b": session_b,
        "delta_routes": b.total_routes - a.total_routes,
        "delta_miles": round(b.total_miles - a.total_miles, 2),
        "delta_cost_usd": round(b.total_cost_usd - a.total_cost_usd, 2),
        "delta_savings_pct": round(b.savings_percent - a.savings_percent, 2),
        "a_summary": {
            "routes": a.total_routes, "miles": a.total_miles,
            "cost": a.total_cost_usd, "savings_pct": a.savings_percent,
            "avg_cube_util": a.average_cube_utilization,
        },
        "b_summary": {
            "routes": b.total_routes, "miles": b.total_miles,
            "cost": b.total_cost_usd, "savings_pct": b.savings_percent,
            "avg_cube_util": b.average_cube_utilization,
        },
    }
