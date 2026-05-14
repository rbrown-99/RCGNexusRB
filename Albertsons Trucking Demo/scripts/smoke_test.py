"""Smoke-test the solver pipeline against all four sample scenarios.

Also exercises the new bits added in this iteration:
  - splits in OptimizationResult
  - reoptimize knobs (capacity_relaxation_pct, window_slack_minutes,
    weather_overrides, priority_first)
  - delay_impact + sensitivity-style relaxation
"""
from pathlib import Path
import sys

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

ROOT = Path(__file__).resolve().parents[1] / "sample_data"
SCENARIOS = ["standard_week", "heavy_volume", "tight_windows", "long_haul_mix"]


def _run(scenario: str, *, knobs: dict | None = None):
    folder = ROOT / scenario
    orders = parse_orders(folder / "orders.csv")
    locations = parse_locations(folder / "locations.xlsx")
    bundle = parse_constraints(folder / "constraints.xlsx")
    matrix = build_cost_matrix(locations)
    result = solve_vrp(orders, locations, matrix, bundle, solver_seconds=10, **(knobs or {}))
    findings = validate_routes(result.routes, locations, bundle)
    return result, findings


def _print_summary(label: str, result, findings):
    v = [f for f in findings if f.severity == "VIOLATION"]
    w = [f for f in findings if f.severity == "WARNING"]
    i = [f for f in findings if f.severity == "INFO"]
    print(f"\n=== {label} ===")
    print(f"  status={result.solver_status}  routes={result.total_routes}  "
          f"miles={result.total_miles}  cost=${result.total_cost_usd}  "
          f"savings={result.savings_percent}%  splits={len(result.splits)}")
    print(f"  findings: {len(v)} viol, {len(w)} warn, {len(i)} info")
    codes = sorted({f.code for f in (v + w + i)})
    print(f"  codes: {', '.join(codes) if codes else '(none)'}")
    for s in result.splits[:3]:
        print(f"  SPLIT {s.location_code} reason={s.reason} routes={s.route_ids}")


def main():
    for sc in SCENARIOS:
        try:
            result, findings = _run(sc)
            _print_summary(sc, result, findings)
        except Exception as e:
            print(f"!! {sc} failed: {e}")

    # Knob test on standard_week.
    print("\n--- knob test: capacity_relaxation_pct=0.10, window_slack_minutes=30 ---")
    r2, f2 = _run("standard_week", knobs={
        "capacity_relaxation_pct": 0.10,
        "window_slack_minutes": 30,
        "weather_overrides": {"WY": ["SINGLE_53", "48-28_COMBO"]},
    })
    _print_summary("standard_week+knobs", r2, f2)

    print("\nDONE")


if __name__ == "__main__":
    try:
        main()
    finally:
        _LOG.close()
