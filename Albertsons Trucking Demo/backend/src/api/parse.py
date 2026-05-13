"""POST /api/parse — accept three uploaded files, return parsed payload."""
from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, File, UploadFile

from ..parser import parse_constraints, parse_locations, parse_orders
from ..state import store

router = APIRouter(prefix="/api", tags=["parse"])


@router.post("/parse")
async def parse_endpoint(
    orders: UploadFile = File(...),
    locations: UploadFile = File(...),
    constraints: UploadFile = File(...),
):
    orders_bytes = await orders.read()
    locations_bytes = await locations.read()
    constraints_bytes = await constraints.read()

    parsed_orders = parse_orders(orders_bytes)
    parsed_locations = parse_locations(BytesIO(locations_bytes))
    parsed_bundle = parse_constraints(BytesIO(constraints_bytes))

    sid = store.create(parsed_orders, parsed_locations, parsed_bundle)
    return {
        "session_id": sid,
        "orders_count": len(parsed_orders),
        "locations_count": len(parsed_locations),
        "trailer_types": [t.trailer_config for t in parsed_bundle.trailer_types],
        "temperature_groups": sorted({o.temperature_group for o in parsed_orders}),
        "commodity_groups": sorted({o.commodity_group for o in parsed_orders}),
    }
