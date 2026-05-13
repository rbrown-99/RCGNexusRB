from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RestrictionType = Literal[
    "INTERSTATE_ONLY",
    "HIGHWAY_RESTRICTION",
    "WEIGHT_LIMIT",
    "UNRESTRICTED",
]


class TrailerConfig(BaseModel):
    trailer_config: str
    description: str
    max_weight_lbs: float = Field(gt=0)
    max_cube_1stop: float = Field(gt=0)
    max_stops: int = Field(gt=0)


class CubeDegradation(BaseModel):
    """Cube capacity by stop count. Index 1..N -> capacity (cubic feet)."""
    trailer_config: str
    cube_by_stops: dict[int, float]

    def cube_for_stops(self, n_stops: int) -> float:
        if n_stops <= 0:
            n_stops = 1
        keys = sorted(self.cube_by_stops)
        if n_stops in self.cube_by_stops:
            return self.cube_by_stops[n_stops]
        # Use largest entry <= n_stops, else smallest available.
        applicable = [k for k in keys if k <= n_stops]
        if applicable:
            return self.cube_by_stops[max(applicable)]
        return self.cube_by_stops[keys[0]]

    @property
    def max_stops(self) -> int:
        return max(self.cube_by_stops) if self.cube_by_stops else 0


class RoadRestriction(BaseModel):
    state: str
    trailer_config: str  # may be "ALL"
    restriction_type: RestrictionType
    restriction_detail: str

    def applies_to(self, trailer_config: str) -> bool:
        return self.trailer_config == "ALL" or self.trailer_config == trailer_config


class CostProxy(BaseModel):
    cost_type: str
    value: float
    unit: str


class ConstraintBundle(BaseModel):
    trailer_types: list[TrailerConfig]
    cube_degradation: list[CubeDegradation]
    road_restrictions: list[RoadRestriction]
    cost_proxies: list[CostProxy]

    def cost(self, key: str, default: float = 0.0) -> float:
        for c in self.cost_proxies:
            if c.cost_type == key:
                return c.value
        return default

    def degradation_for(self, trailer_config: str) -> CubeDegradation | None:
        for d in self.cube_degradation:
            if d.trailer_config == trailer_config:
                return d
        return None

    def trailer(self, trailer_config: str) -> TrailerConfig | None:
        for t in self.trailer_types:
            if t.trailer_config == trailer_config:
                return t
        return None
