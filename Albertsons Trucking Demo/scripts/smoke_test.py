"""Smoke-test the solver pipeline against sample data."""
from pathlib import Path
import sys
import traceback

# Tee output to a file so we can capture it even if the shell swallows stdout.
_LOG = open(Path(__file__).with_name("smoke_out.txt"), "w", encoding="utf-8")
class _Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, s):
        for st in self.streams:
            st.write(s); st.flush()
    def flush(self):
        for st in self.streams: st.flush()
sys.stdout = _Tee(sys.__stdout__, _LOG)
sys.stderr = _Tee(sys.__stderr__, _LOG)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from src.parser import parse_orders, parse_locations, parse_constraints  # noqa: E402
from src.solver import build_cost_matrix, solve_vrp, validate_routes      # noqa: E402

root = Path(__file__).resolve().parents[1] / "sample_data"
orders = parse_orders(root / "sample_orders.csv")
locations = parse_locations(root / "sample_locations.xlsx")
bundle = parse_constraints(root / "sample_constraints.xlsx")

matrix = build_cost_matrix(locations)
result = solve_vrp(orders, locations, matrix, bundle, solver_seconds=15)

print("STATUS:", result.solver_status, "SECS:", result.solve_seconds)
print("ROUTES:", result.total_routes,
      "MILES:", result.total_miles,
      "COST:", result.total_cost_usd)
print("NAIVE:", result.naive_baseline.total_cost_usd,
      "SAVINGS:", result.savings_percent, "PCT")
print("UTIL cube/wt:", result.average_cube_utilization,
      result.average_weight_utilization)
for r in result.routes:
    print(r.route_id, len(r.stops), "stops", r.total_miles, "mi",
          "cube", round(r.cube_utilization * 100),
          "wt", round(r.weight_utilization * 100),
          "states", r.states_traversed, "on_time", r.on_time)
findings = validate_routes(result.routes, locations, bundle)
v = [f for f in findings if f.severity == "VIOLATION"]
w = [f for f in findings if f.severity == "WARNING"]
print("FINDINGS:", len(v), "viol", len(w), "warn")
for f in (v + w)[:8]:
    print(" ", f.severity, f.code, f.message)
_LOG.close()
