"""Cost matrix builder.

Uses Azure Maps Route Matrix API when AZURE_MAPS_KEY is set; otherwise falls back
to a haversine-distance approximation (great-circle distance x 1.3 road factor,
travel time at 55 mph average).
"""
from __future__ import annotations

import asyncio
import math
import os
from dataclasses import dataclass
from typing import Sequence

import httpx

from ..models import Location


EARTH_RADIUS_MI = 3958.7613
ROAD_FACTOR = 1.3
AVG_TRUCK_SPEED_MPH = 55.0


@dataclass
class CostMatrix:
    location_codes: list[str]                     # in matrix order
    distances_miles: list[list[float]]            # NxN
    times_minutes: list[list[float]]              # NxN
    used_azure_maps: bool

    def index_of(self, code: str) -> int:
        return self.location_codes.index(code)


def _haversine_miles(a: Location, b: Location) -> float:
    lat1, lon1 = math.radians(a.latitude), math.radians(a.longitude)
    lat2, lon2 = math.radians(b.latitude), math.radians(b.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def _haversine_matrix(locations: Sequence[Location]) -> tuple[list[list[float]], list[list[float]]]:
    n = len(locations)
    dist = [[0.0] * n for _ in range(n)]
    time = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            miles = _haversine_miles(locations[i], locations[j]) * ROAD_FACTOR
            dist[i][j] = miles
            time[i][j] = (miles / AVG_TRUCK_SPEED_MPH) * 60.0
    return dist, time


async def _azure_maps_matrix(
    locations: Sequence[Location], api_key: str
) -> tuple[list[list[float]], list[list[float]]]:
    """Call Azure Maps Route Matrix v2 (truck profile)."""
    n = len(locations)
    coords = [{"latitude": loc.latitude, "longitude": loc.longitude} for loc in locations]
    body = {
        "origins": {"type": "MultiPoint", "coordinates": [[c["longitude"], c["latitude"]] for c in coords]},
        "destinations": {"type": "MultiPoint", "coordinates": [[c["longitude"], c["latitude"]] for c in coords]},
    }
    params = {
        "api-version": "1.0",
        "routeType": "fastest",
        "travelMode": "truck",
        "subscription-key": api_key,
    }
    url = "https://atlas.microsoft.com/route/matrix/sync/json"
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, params=params, json=body)
        r.raise_for_status()
        data = r.json()
    matrix = data.get("matrix", [])
    dist = [[0.0] * n for _ in range(n)]
    tmin = [[0.0] * n for _ in range(n)]
    for i, row in enumerate(matrix):
        for j, cell in enumerate(row):
            if i == j:
                continue
            summary = (cell or {}).get("response", {}).get("routeSummary", {})
            dist[i][j] = (summary.get("lengthInMeters", 0) or 0) / 1609.344
            tmin[i][j] = (summary.get("travelTimeInSeconds", 0) or 0) / 60.0
    return dist, tmin


def build_cost_matrix(locations: Sequence[Location]) -> CostMatrix:
    """Synchronous entrypoint: tries Azure Maps if key present, else haversine."""
    codes = [loc.location_code for loc in locations]
    api_key = os.getenv("AZURE_MAPS_KEY", "").strip()

    if api_key:
        try:
            dist, tmin = asyncio.run(_azure_maps_matrix(locations, api_key))
            return CostMatrix(codes, dist, tmin, used_azure_maps=True)
        except Exception:
            # graceful fallback if Azure Maps fails
            pass

    dist, tmin = _haversine_matrix(locations)
    return CostMatrix(codes, dist, tmin, used_azure_maps=False)
