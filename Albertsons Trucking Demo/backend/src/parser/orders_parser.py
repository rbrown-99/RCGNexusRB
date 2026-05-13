from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import pandas as pd
from pydantic import ValidationError

from ..models import Order


REQUIRED_COLS = {
    "order_id", "location_code", "commodity_group", "temperature_group",
    "weight_lbs", "cube", "cases", "is_crossdock", "order_source",
    "order_date", "required_delivery_date",
}


def _read(source: str | Path | bytes | io.IOBase) -> pd.DataFrame:
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.suffix.lower() in (".xlsx", ".xls"):
            return pd.read_excel(path)
        return pd.read_csv(path)
    if isinstance(source, bytes):
        # try CSV first, fall back to xlsx
        try:
            return pd.read_csv(io.BytesIO(source))
        except Exception:
            return pd.read_excel(io.BytesIO(source))
    if isinstance(source, io.IOBase):
        try:
            return pd.read_csv(source)
        except Exception:
            source.seek(0)
            return pd.read_excel(source)
    raise TypeError(f"unsupported source type {type(source)}")


def parse_orders(source: str | Path | bytes | io.IOBase) -> list[Order]:
    df = _read(source)
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"orders file missing columns: {sorted(missing)}")

    orders: list[Order] = []
    errors: list[str] = []
    for i, row in df.iterrows():
        try:
            orders.append(Order(**row.to_dict()))
        except ValidationError as e:
            errors.append(f"row {i}: {e.errors()[0]['msg']}")
    if errors:
        raise ValueError("invalid orders: " + "; ".join(errors[:5]))
    return orders


def aggregate_demand(orders: Iterable[Order]) -> dict[tuple[str, str], dict]:
    """Aggregate orders by (location_code, temperature_group)."""
    agg: dict[tuple[str, str], dict] = {}
    for o in orders:
        key = (o.location_code, o.temperature_group)
        bucket = agg.setdefault(key, {
            "location_code": o.location_code,
            "temperature_group": o.temperature_group,
            "weight_lbs": 0.0,
            "cube": 0.0,
            "cases": 0,
            "order_ids": [],
        })
        bucket["weight_lbs"] += float(o.weight_lbs)
        bucket["cube"] += float(o.cube)
        bucket["cases"] += int(o.cases)
        bucket["order_ids"].append(o.order_id)
    return agg
