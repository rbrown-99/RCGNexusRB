"""POST /api/sensitivity/lcv-availability/{session_id} — fleet sensitivity.

Q12 / Q20 — "what if we had +N units of trailer config X tomorrow?"

This re-runs the optimization with an effectively larger fleet of the requested
trailer config. We don't model individual physical units in the demo (the solver
already builds a capacity-rich vehicle pool), so the practical lever is:

  * Drop the requested trailer config out of the bundle (== unavailable),
  * Or relax weight/cube to simulate having extra capacity headroom.

For the LCV question specifically, the user is asking what happens when MORE LCVs
are available — the current solver already has plenty of headroom, so the more
honest answer is "with the current 32-store dataset adding LCVs doesn't change
the plan; binding constraint is X" (returned in the response). When the dataset
or capacity_relaxation pushes us against the wall, this tool shows real deltas.

Body:
  {
    "extra_lcv_units": 2,
    "lcv_trailer_config": "SINGLE_53"   # which config we have more of
  }

Response:
  {
    "session_id": "...",
    "extra_lcv_units": 2,
    "lcv_trailer_config": "SINGLE_53",
    "baseline": { total_routes, total_cost_usd, total_miles, lcv_routes_used },
    "scenario": { total_routes, total_cost_usd, total_miles, lcv_routes_used },
    "delta": { routes, cost_usd, miles },
    "summary": "..."
  }

Note: "extra_lcv_units" is reported in the considerations only; the solver
already pre-allocates a capacity-rich pool so the gain is realized when the
binding constraint is fleet count rather than capacity. See agent docs.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from ..solver import build_cost_matrix, solve_vrp, validate_routes
from ..state import store

router = APIRouter(prefix="/api", tags=["sensitivity"])


def _summarize(result, lcv_config: str) -> dict:
    lcv_routes = sum(1 for r in result.routes if r.trailer_config == lcv_config)
    return {
        "total_routes": result.total_routes,
        "total_cost_usd": result.total_cost_usd,
        "total_miles": result.total_miles,
        "lcv_routes_used": lcv_routes,
        "average_weight_utilization": result.average_weight_utilization,
        "average_cube_utilization": result.average_cube_utilization,
    }


@router.post("/sensitivity/lcv-availability/{session_id}")
async def lcv_sensitivity(session_id: str, body: dict = Body(default_factory=dict)):
    try:
        sess = store.get(session_id)
    except KeyError:
        raise HTTPException(404, "unknown session")

    baseline_result = sess.get("result")
    if not baseline_result:
        raise HTTPException(400, "session has no baseline result; run /api/optimize first")

    try:
        extra_units = int(body.get("extra_lcv_units", 0))
    except (TypeError, ValueError):
        raise HTTPException(400, "extra_lcv_units must be an integer")
    if extra_units < 0 or extra_units > 50:
        raise HTTPException(400, "extra_lcv_units must be between 0 and 50")
    lcv_config = body.get("lcv_trailer_config") or "SINGLE_53"

    bundle = sess["bundle"]
    if not any(t.trailer_config == lcv_config for t in bundle.trailer_types):
        raise HTTPException(400, f"trailer config {lcv_config!r} not present in current constraints")

    # Re-run the solve. The solver's internal _build_vehicle_fleet already
    # provisions plenty of vehicles per trailer config, so the practical
    # mechanism here is rerunning under the same bundle and reporting the
    # delta. With the extra-units knob we ALSO bump the capacity headroom
    # slightly to simulate "more LCV miles available" (proxy for queueing
    # relief in an underprovisioned fleet).
    relaxation_proxy = min(0.10, 0.02 * extra_units)  # 2% per unit, capped at 10%

    matrix = build_cost_matrix(sess["locations"])
    scenario_result = solve_vrp(
        sess["orders"], sess["locations"], matrix, bundle,
        capacity_relaxation_pct=relaxation_proxy,
    )
    findings = validate_routes(scenario_result.routes, sess["locations"], bundle)
    for f in findings:
        scenario_result.exceptions.append(f)

    base = _summarize(baseline_result, lcv_config)
    sc = _summarize(scenario_result, lcv_config)
    delta = {
        "routes": sc["total_routes"] - base["total_routes"],
        "cost_usd": round(sc["total_cost_usd"] - base["total_cost_usd"], 2),
        "miles": round(sc["total_miles"] - base["total_miles"], 2),
        "lcv_routes_used": sc["lcv_routes_used"] - base["lcv_routes_used"],
    }

    if delta["cost_usd"] < 0 or delta["routes"] < 0:
        impact = (
            f"Adding {extra_units} more {lcv_config} unit(s) cuts cost by "
            f"${abs(delta['cost_usd']):,.0f} and uses {sc['lcv_routes_used']} of them."
        )
    elif delta["routes"] == 0 and abs(delta["cost_usd"]) < 1:
        impact = (
            f"Current dataset is not capacity-bound for {lcv_config}; "
            f"adding {extra_units} unit(s) makes no measurable difference. "
            f"Binding constraint is likely store count or geographic spread."
        )
    else:
        impact = (
            f"Scenario reshuffled to use {sc['lcv_routes_used']} {lcv_config} routes "
            f"(was {base['lcv_routes_used']}). Net cost change: ${delta['cost_usd']:+,.0f}."
        )

    return {
        "session_id": session_id,
        "extra_lcv_units": extra_units,
        "lcv_trailer_config": lcv_config,
        "baseline": base,
        "scenario": sc,
        "delta": delta,
        "summary": impact,
    }
