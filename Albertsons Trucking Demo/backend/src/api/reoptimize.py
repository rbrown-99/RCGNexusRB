"""POST /api/reoptimize — re-run after a what-if delta.

Supported deltas (all optional, in JSON body):
  * remove_orders: [order_id, ...]                       — pretend these orders don't exist
  * remove_locations: [location_code, ...]               — drop a store entirely
  * remove_trailer_configs: [config, ...]                — pretend that fleet is unavailable
  * extra_consideration: str                              — free-form note added to result.considerations
  * capacity_relaxation_pct: float                        — Q5  loosen weight + cube by N% on all trailers
  * window_slack_minutes: int                             — Q6  widen every store delivery window by N min on each side
  * priority_first: [location_code, ...]                  — Q11 force these stores to be the first stop on their assigned route
  * weather_overrides: {state_code: [trailer_config,...]} — Q21 in this state, only these trailer configs may operate
"""
from __future__ import annotations

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

    # Phase 2 knobs
    try:
        capacity_relaxation_pct = float(body.get("capacity_relaxation_pct") or 0.0)
    except (TypeError, ValueError):
        raise HTTPException(400, "capacity_relaxation_pct must be a number (e.g. 0.05 for 5%)")
    if capacity_relaxation_pct < 0 or capacity_relaxation_pct > 0.5:
        raise HTTPException(400, "capacity_relaxation_pct must be between 0 and 0.5")
    try:
        window_slack_minutes = int(body.get("window_slack_minutes") or 0)
    except (TypeError, ValueError):
        raise HTTPException(400, "window_slack_minutes must be an integer")
    if window_slack_minutes < 0 or window_slack_minutes > 480:
        raise HTTPException(400, "window_slack_minutes must be between 0 and 480 (8 hours)")
    priority_first = body.get("priority_first") or []
    if not isinstance(priority_first, list):
        raise HTTPException(400, "priority_first must be a list of location codes")
    weather_overrides = body.get("weather_overrides") or {}
    if not isinstance(weather_overrides, dict):
        raise HTTPException(400, "weather_overrides must be a dict {state: [trailer_config,...]}")
    for k, v in weather_overrides.items():
        if not isinstance(v, list):
            raise HTTPException(400, f"weather_overrides[{k!r}] must be a list of trailer configs")

    new_orders = [o for o in orders if o.order_id not in remove_orders and o.location_code not in remove_locations]
    new_locations = [l for l in locations if l.location_code not in remove_locations]
    new_bundle = ConstraintBundle(
        trailer_types=[t for t in bundle.trailer_types if t.trailer_config not in remove_trailer_configs],
        cube_degradation=bundle.cube_degradation,
        road_restrictions=bundle.road_restrictions,
        cost_proxies=bundle.cost_proxies,
    )

    matrix = build_cost_matrix(new_locations)
    result = solve_vrp(
        new_orders, new_locations, matrix, new_bundle,
        capacity_relaxation_pct=capacity_relaxation_pct,
        window_slack_minutes=window_slack_minutes,
        weather_overrides=weather_overrides,
        priority_first=priority_first,
    )
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

    # Persist updated state so /api/explain and /api/delay-impact still work
    sess["result"] = result

    return {"session_id": session_id, "result": result.model_dump()}
