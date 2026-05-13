"""POST /api/reoptimize — re-run after a what-if delta.

Supported deltas (all optional, in JSON body):
  * remove_orders: [order_id, ...]  — pretend these orders don't exist
  * remove_locations: [location_code, ...]  — drop a store entirely
  * remove_trailer_configs: [config, ...]   — pretend that fleet is unavailable
  * extra_consideration: str (free-form note added to result.considerations)
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Body, HTTPException

from ..models import ConstraintBundle
from ..solver import build_cost_matrix, solve_vrp, validate_routes
from ..state import store

router = APIRouter(prefix="/api", tags=["reoptimize"])


@router.post("/reoptimize/{session_id}")
async def reoptimize_endpoint(
    session_id: str,
    body: dict = Body(default_factory=dict),
):
    try:
        sess = store.get(session_id)
    except KeyError:
        raise HTTPException(404, "unknown session")

    orders = sess["orders"]
    locations = sess["locations"]
    bundle: ConstraintBundle = sess["bundle"]

    remove_orders = set(body.get("remove_orders", []))
    remove_locations = set(body.get("remove_locations", []))
    remove_trailer_configs = set(body.get("remove_trailer_configs", []))
    extra = body.get("extra_consideration")

    new_orders = [o for o in orders if o.order_id not in remove_orders and o.location_code not in remove_locations]
    new_locations = [l for l in locations if l.location_code not in remove_locations]
    new_bundle = ConstraintBundle(
        trailer_types=[t for t in bundle.trailer_types if t.trailer_config not in remove_trailer_configs],
        cube_degradation=bundle.cube_degradation,
        road_restrictions=bundle.road_restrictions,
        cost_proxies=bundle.cost_proxies,
    )

    matrix = build_cost_matrix(new_locations)
    result = solve_vrp(new_orders, new_locations, matrix, new_bundle)
    findings = validate_routes(result.routes, new_locations, new_bundle)
    for f in findings:
        result.exceptions.append(f)
    if extra:
        result.considerations.append(f"What-if: {extra}")
    if remove_orders:
        result.considerations.append(f"What-if: dropped {len(remove_orders)} orders")
    if remove_locations:
        result.considerations.append(f"What-if: dropped locations {sorted(remove_locations)}")
    if remove_trailer_configs:
        result.considerations.append(f"What-if: trailer configs unavailable {sorted(remove_trailer_configs)}")

    return {"session_id": session_id, "result": result.model_dump()}
