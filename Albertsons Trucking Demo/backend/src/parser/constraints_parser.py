from __future__ import annotations

import io
import math
from pathlib import Path

import pandas as pd

from ..models import (
    ConstraintBundle,
    CostProxy,
    CubeDegradation,
    RoadRestriction,
    TrailerConfig,
)


def _read_sheet(source, sheet: str) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        return pd.read_excel(source, sheet_name=sheet)
    if isinstance(source, bytes):
        return pd.read_excel(io.BytesIO(source), sheet_name=sheet)
    if isinstance(source, io.IOBase):
        return pd.read_excel(source, sheet_name=sheet)
    raise TypeError(f"unsupported source type {type(source)}")


def parse_constraints(source) -> ConstraintBundle:
    trailer_df = _read_sheet(source, "trailer_types")
    deg_df = _read_sheet(source, "cube_degradation")
    road_df = _read_sheet(source, "state_road_restrictions")
    cost_df = _read_sheet(source, "cost_proxies")

    trailers = [TrailerConfig(**r.to_dict()) for _, r in trailer_df.iterrows()]

    degradations: list[CubeDegradation] = []
    stop_cols = [c for c in deg_df.columns if c.startswith("stops_")]
    for _, row in deg_df.iterrows():
        cube_by_stops: dict[int, float] = {}
        for col in stop_cols:
            v = row[col]
            if v is None or (isinstance(v, float) and math.isnan(v)):
                continue
            try:
                n = int(col.split("_", 1)[1])
                cube_by_stops[n] = float(v)
            except (TypeError, ValueError):
                continue
        degradations.append(
            CubeDegradation(trailer_config=row["trailer_config"], cube_by_stops=cube_by_stops)
        )

    road_restrictions = [RoadRestriction(**r.to_dict()) for _, r in road_df.iterrows()]
    cost_proxies = [CostProxy(**r.to_dict()) for _, r in cost_df.iterrows()]

    return ConstraintBundle(
        trailer_types=trailers,
        cube_degradation=degradations,
        road_restrictions=road_restrictions,
        cost_proxies=cost_proxies,
    )
