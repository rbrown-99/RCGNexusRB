from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, field_validator


LocationType = Literal["DC", "STORE", "BACKHAUL", "VENDOR"]


def _parse_hhmm(value) -> time:
    if isinstance(value, time):
        return value
    s = str(value).strip()
    if ":" not in s:
        # excel may give something like 6.0 -> 06:00
        try:
            h = int(float(s))
            return time(hour=h, minute=0)
        except ValueError:
            raise ValueError(f"invalid time {value!r}")
    h, m = s.split(":", 1)
    return time(hour=int(h), minute=int(m))


class Location(BaseModel):
    location_code: str
    location_name: str
    location_type: LocationType
    address: str
    city: str
    state: str
    zip: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    delivery_window_open: time
    delivery_window_close: time
    delivery_days: list[str]
    dock_doors: int = Field(ge=0)
    max_trailer_length_ft: int = Field(gt=0)

    @field_validator("delivery_window_open", "delivery_window_close", mode="before")
    @classmethod
    def _coerce_time(cls, v):
        return _parse_hhmm(v)

    @field_validator("delivery_days", mode="before")
    @classmethod
    def _split_days(cls, v):
        if isinstance(v, list):
            return [d.strip().upper() for d in v]
        return [d.strip().upper() for d in str(v).split(",") if d.strip()]

    @field_validator("zip", mode="before")
    @classmethod
    def _zip_str(cls, v):
        return str(v).strip()
