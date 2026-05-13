from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from ..models import Location


REQUIRED_COLS = {
    "location_code", "location_name", "location_type", "address", "city",
    "state", "zip", "latitude", "longitude",
    "delivery_window_open", "delivery_window_close", "delivery_days",
    "dock_doors", "max_trailer_length_ft",
}


def _read(source: str | Path | bytes | io.IOBase) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        return pd.read_excel(source, sheet_name="locations")
    if isinstance(source, bytes):
        return pd.read_excel(io.BytesIO(source), sheet_name="locations")
    if isinstance(source, io.IOBase):
        return pd.read_excel(source, sheet_name="locations")
    raise TypeError(f"unsupported source type {type(source)}")


def parse_locations(source: str | Path | bytes | io.IOBase) -> list[Location]:
    df = _read(source)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"locations file missing columns: {sorted(missing)}")

    out: list[Location] = []
    errors: list[str] = []
    for i, row in df.iterrows():
        d = row.to_dict()
        # excel sometimes converts HH:MM into datetime.time already; pydantic handles via field_validator.
        try:
            out.append(Location(**d))
        except ValidationError as e:
            errors.append(f"row {i}: {e.errors()[0]['msg']}")
    if errors:
        raise ValueError("invalid locations: " + "; ".join(errors[:5]))
    return out
