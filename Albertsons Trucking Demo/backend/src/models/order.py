from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


CommodityGroup = Literal["DRY", "FROZEN", "REFRIGERATED", "PRODUCE"]
TemperatureGroup = Literal["AMBIENT", "COOLER_34_38F", "FREEZER_0F"]
OrderSource = Literal["COSMOS", "VENDOR_CSV"]


class Order(BaseModel):
    order_id: str
    location_code: str
    commodity_group: CommodityGroup
    temperature_group: TemperatureGroup
    weight_lbs: float = Field(gt=0)
    cube: float = Field(gt=0)
    cases: int = Field(gt=0)
    is_crossdock: bool
    order_source: OrderSource
    order_date: date
    required_delivery_date: date

    @field_validator("is_crossdock", mode="before")
    @classmethod
    def _coerce_bool(cls, v):
        if isinstance(v, str):
            return v.strip().upper() in ("TRUE", "T", "YES", "1")
        return bool(v)
