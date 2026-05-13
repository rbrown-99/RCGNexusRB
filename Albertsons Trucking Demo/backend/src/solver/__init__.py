"""Solver components: cost matrix, VRP, validator, constraint encoder."""
from .cost_matrix import build_cost_matrix
from .vrp_solver import solve_vrp
from .route_validator import validate_routes
from .constraint_encoder import encode_constraints

__all__ = ["build_cost_matrix", "solve_vrp", "validate_routes", "encode_constraints"]
