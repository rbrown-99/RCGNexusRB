"""POST /api/explain — natural language explanation of why a route looks the way it does.

Returns a structured payload (the agent layer turns it into prose).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..solver.constraint_encoder import effective_weight_capacity, relevant_restrictions
from ..state import store

router = APIRouter(prefix="/api", tags=["explain"])


@router.get("/explain/{session_id}/{route_id}")
async def explain(session_id: str, route_id: str):
    try:
        sess = store.get(session_id)
    except KeyError:
        raise HTTPException(404, "unknown session")
    result = sess.get("result")
    if not result:
        raise HTTPException(400, "session has no result")
    route = next((r for r in result.routes if r.route_id == route_id), None)
    if not route:
        raise HTTPException(404, f"route {route_id} not found")

    bundle = sess["bundle"]
    trailer = bundle.trailer(route.trailer_config)
    degradation = bundle.degradation_for(route.trailer_config)
    eff_weight = effective_weight_capacity(bundle, trailer, route.states_traversed) if trailer else None
    eff_cube = degradation.cube_for_stops(len(route.stops)) if degradation else None
    restrictions = relevant_restrictions(bundle, trailer, route.states_traversed) if trailer else []

    return {
        "route_id": route.route_id,
        "trailer_config": route.trailer_config,
        "temperature_group": route.temperature_group,
        "stop_count": len(route.stops),
        "stops": [s.location_code for s in route.stops],
        "states_traversed": route.states_traversed,
        "total_miles": route.total_miles,
        "estimated_cost_usd": route.estimated_cost_usd,
        "weight_lbs": route.total_weight_lbs,
        "weight_capacity_lbs_effective": eff_weight,
        "weight_utilization_pct": round(route.weight_utilization * 100, 1),
        "cube": route.total_cube,
        "cube_capacity_effective": eff_cube,
        "cube_utilization_pct": round(route.cube_utilization * 100, 1),
        "on_time": route.on_time,
        "applied_restrictions": restrictions,
        "rationale": [
            f"Routes are split by temperature group; this is {route.temperature_group}.",
            f"Cube cap reduced to {eff_cube} given {len(route.stops)} stops via cube-degradation chart." if eff_cube else "",
            f"Weight cap effective {eff_weight} lbs across states {route.states_traversed}." if eff_weight else "",
            *([f"Trailer note: {r}" for r in restrictions]),
        ],
    }
