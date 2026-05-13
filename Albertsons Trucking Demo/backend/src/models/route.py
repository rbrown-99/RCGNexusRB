from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Severity = Literal["INFO", "WARNING", "VIOLATION"]


class Exception_(BaseModel):
    """Validation finding (violation, warning, or info)."""
    severity: Severity
    code: str
    message: str
    route_id: str | None = None
    location_code: str | None = None


class RouteStop(BaseModel):
    sequence: int
    location_code: str
    location_name: str
    latitude: float
    longitude: float
    arrival_minutes_from_start: float
    departure_minutes_from_start: float
    weight_delivered_lbs: float
    cube_delivered: float
    order_ids: list[str]
    on_time: bool


class Route(BaseModel):
    route_id: str
    trailer_config: str
    temperature_group: str
    stops: list[RouteStop]
    total_miles: float
    total_minutes: float
    total_weight_lbs: float
    total_cube: float
    weight_capacity_lbs: float
    cube_capacity: float
    weight_utilization: float = Field(ge=0)
    cube_utilization: float = Field(ge=0)
    estimated_cost_usd: float
    on_time: bool
    states_traversed: list[str]


class NaiveBaseline(BaseModel):
    """One truck per (location, temp_group) baseline for cost comparison."""
    total_routes: int
    total_miles: float
    total_cost_usd: float


class OptimizationResult(BaseModel):
    routes: list[Route]
    exceptions: list[Exception_]
    considerations: list[str]  # "Applied: cube degradation by stop count", etc.
    relaxed_constraints: list[str]
    total_routes: int
    total_miles: float
    total_cost_usd: float
    average_weight_utilization: float
    average_cube_utilization: float
    naive_baseline: NaiveBaseline
    savings_usd: float
    savings_percent: float
    solver_status: str
    solve_seconds: float
