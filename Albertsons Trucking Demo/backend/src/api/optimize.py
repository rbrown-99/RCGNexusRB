"""POST /api/optimize — run full pipeline."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import settings
from ..parser import parse_constraints, parse_locations, parse_orders
from .. import persistence
from ..solver import build_cost_matrix, solve_vrp, validate_routes
from ..state import store

router = APIRouter(prefix="/api", tags=["optimize"])


def _run_pipeline(orders, locations, bundle, solver_seconds: int):
    matrix = build_cost_matrix(locations)
    result = solve_vrp(orders, locations, matrix, bundle, solver_seconds=solver_seconds)
    findings = validate_routes(result.routes, locations, bundle)
    # merge validator findings into result.exceptions (keep solver ones first)
    existing_codes = {(e.code, e.route_id, e.location_code) for e in result.exceptions}
    for f in findings:
        key = (f.code, f.route_id, f.location_code)
        if key not in existing_codes:
            result.exceptions.append(f)
    return result, matrix


@router.post("/optimize")
async def optimize_endpoint(
    orders: Optional[UploadFile] = File(None),
    locations: Optional[UploadFile] = File(None),
    constraints: Optional[UploadFile] = File(None),
    session_id: Optional[str] = Form(None),
    solver_seconds: Optional[int] = Form(None),
):
    secs = solver_seconds or settings.solver_seconds

    if session_id:
        try:
            sess = store.get(session_id)
        except KeyError:
            raise HTTPException(404, f"unknown session_id {session_id}")
        result, matrix = _run_pipeline(sess["orders"], sess["locations"], sess["bundle"], secs)
        store.update_result(session_id, result)
        persistence.save_optimization_run(
            session_id, kind="optimize", result=result,
            distance_source="azure_maps" if matrix.used_azure_maps else "haversine_fallback",
        )
        return {"session_id": session_id, "result": result.model_dump()}

    if not (orders and locations and constraints):
        raise HTTPException(400, "provide either session_id or orders+locations+constraints uploads")

    parsed_orders = parse_orders(await orders.read())
    parsed_locations = parse_locations(BytesIO(await locations.read()))
    parsed_bundle = parse_constraints(BytesIO(await constraints.read()))
    sid = store.create(parsed_orders, parsed_locations, parsed_bundle)
    persistence.save_session(
        sid, n_orders=len(parsed_orders), n_locations=len(parsed_locations),
        n_constraints=1, source="upload",
    )
    persistence.save_purchase_orders(sid, parsed_orders)
    result, matrix = _run_pipeline(parsed_orders, parsed_locations, parsed_bundle, secs)
    store.update_result(sid, result)
    persistence.save_optimization_run(
        sid, kind="optimize", result=result,
        distance_source="azure_maps" if matrix.used_azure_maps else "haversine_fallback",
    )
    return {"session_id": sid, "result": result.model_dump()}


@router.post("/optimize-from-samples")
async def optimize_from_samples(solver_seconds: Optional[int] = None, scenario: Optional[str] = None):
    """Convenience endpoint that runs against the bundled sample dataset.

    Pass ?scenario=<key> (standard_week | heavy_volume | tight_windows | long_haul_mix)
    to load that scenario's data. Defaults to standard_week (legacy flat layout).
    """
    secs = solver_seconds or settings.solver_seconds
    base = Path(settings.sample_data_dir).resolve()
    if not base.exists():
        # try repo-relative fallback
        base = Path(__file__).resolve().parents[3] / "sample_data"

    chosen = scenario or "standard_week"
    scenario_dir = base / chosen
    if scenario and not scenario_dir.exists():
        raise HTTPException(404, f"unknown scenario {scenario!r}")

    if scenario_dir.exists():
        orders_path = scenario_dir / "orders.csv"
        locations_path = scenario_dir / "locations.xlsx"
        constraints_path = scenario_dir / "constraints.xlsx"
    else:
        # legacy flat layout fallback
        orders_path = base / "sample_orders.csv"
        locations_path = base / "sample_locations.xlsx"
        constraints_path = base / "sample_constraints.xlsx"

    parsed_orders = parse_orders(orders_path)
    parsed_locations = parse_locations(locations_path)
    parsed_bundle = parse_constraints(constraints_path)
    sid = store.create(parsed_orders, parsed_locations, parsed_bundle)
    persistence.save_session(
        sid, n_orders=len(parsed_orders), n_locations=len(parsed_locations),
        n_constraints=1, source=f"samples:{chosen}",
    )
    persistence.save_purchase_orders(sid, parsed_orders)
    result, matrix = _run_pipeline(parsed_orders, parsed_locations, parsed_bundle, secs)
    store.update_result(sid, result)
    persistence.save_optimization_run(
        sid, kind="optimize", result=result,
        distance_source="azure_maps" if matrix.used_azure_maps else "haversine_fallback",
    )
    return {
        "session_id": sid,
        "scenario": chosen,
        "distance_source": "azure_maps" if matrix.used_azure_maps else "haversine_fallback",
        "result": result.model_dump(),
    }
