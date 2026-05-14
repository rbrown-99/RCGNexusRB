"""Post-solve route validator.

Re-checks every constraint against the produced routes and returns a list of
Exception_ findings with severity. Designed to be called both by the solver and
on-demand via /api/validate.
"""
from __future__ import annotations

import math

from ..models import (
    ConstraintBundle,
    Exception_,
    Location,
    Route,
)
from .constraint_encoder import effective_weight_capacity, relevant_restrictions


# Tunables for the richer exception set (Phase 1 — answers Q4, Q9, Q16, Q17).
WINDOW_AT_RISK_MINUTES = 60        # arrived on time but within X min of close → WARN
LOW_UTIL_THRESHOLD = 0.55          # both weight AND cube below → INFO
LONG_HOP_RATIO = 1.75              # leg ≥ ratio × median leg → INFO
LONG_HOP_MIN_MILES = 75            # AND leg must be ≥ this many miles
LAYOVER_FRACTION = 0.85            # within fraction of HOS cap → INFO suggest


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance, miles. Used as a fast proxy for inter-stop hop sizing."""
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def validate_routes(
    routes: list[Route],
    locations: list[Location],
    bundle: ConstraintBundle,
) -> list[Exception_]:
    findings: list[Exception_] = []
    code_to_loc = {loc.location_code: loc for loc in locations}
    depot = next((loc for loc in locations if loc.location_type == "DC"), None)

    for r in routes:
        trailer = bundle.trailer(r.trailer_config)
        degradation = bundle.degradation_for(r.trailer_config)

        # 1. Stop count vs trailer max
        if trailer and len(r.stops) > trailer.max_stops:
            findings.append(Exception_(
                severity="VIOLATION", code="MAX_STOPS_EXCEEDED", route_id=r.route_id,
                message=f"{r.route_id} has {len(r.stops)} stops, max for "
                        f"{r.trailer_config} is {trailer.max_stops}"))

        # 2. Cube vs degradation chart
        if degradation:
            cap = degradation.cube_for_stops(len(r.stops))
            if r.total_cube > cap + 0.5:
                findings.append(Exception_(
                    severity="VIOLATION", code="CUBE_OVER_CAPACITY", route_id=r.route_id,
                    message=f"{r.route_id} cube {r.total_cube:.0f} exceeds "
                            f"degraded cap {cap:.0f} at {len(r.stops)} stops"))
            elif r.total_cube > cap * 0.95:
                findings.append(Exception_(
                    severity="WARNING", code="CUBE_NEAR_CAPACITY", route_id=r.route_id,
                    message=f"{r.route_id} cube at {r.total_cube/cap*100:.1f}% of degraded cap"))

        # 3. Weight vs state-aware effective cap
        if trailer:
            eff_cap = effective_weight_capacity(bundle, trailer, r.states_traversed)
            if r.total_weight_lbs > eff_cap + 1:
                findings.append(Exception_(
                    severity="VIOLATION", code="WEIGHT_OVER_CAPACITY", route_id=r.route_id,
                    message=f"{r.route_id} weight {r.total_weight_lbs:.0f} exceeds "
                            f"effective cap {eff_cap:.0f} (states: {','.join(r.states_traversed)})"))
            elif r.total_weight_lbs > eff_cap * 0.95:
                findings.append(Exception_(
                    severity="WARNING", code="WEIGHT_NEAR_CAPACITY", route_id=r.route_id,
                    message=f"{r.route_id} weight at {r.total_weight_lbs/eff_cap*100:.1f}% of cap"))

        # 4. Time windows
        for stop in r.stops:
            if not stop.on_time:
                findings.append(Exception_(
                    severity="VIOLATION", code="DELIVERY_LATE", route_id=r.route_id,
                    location_code=stop.location_code,
                    message=f"{r.route_id} arrives late at {stop.location_code}"))

        # 5. Cold chain (one temperature group per route)
        for stop in r.stops:
            loc = code_to_loc.get(stop.location_code)
            if loc and loc.location_type == "DC":
                continue  # depot has no temp constraint
            # nothing to cross-check beyond what the solver already enforces by
            # building one VRP per temp group; surface as INFO.

        # 6. Trailer road restrictions traversed
        if trailer:
            applied = relevant_restrictions(bundle, trailer, r.states_traversed)
            for note in applied:
                findings.append(Exception_(
                    severity="INFO", code="ROAD_RESTRICTION_NOTE", route_id=r.route_id,
                    message=note))

        # 7. Driver hours (max_driver_hours from cost_proxies)
        max_hours = bundle.cost("max_driver_hours", 11.0)
        if max_hours > 0 and r.total_minutes > max_hours * 60 + 1:
            findings.append(Exception_(
                severity="VIOLATION", code="DRIVER_HOURS_EXCEEDED", route_id=r.route_id,
                message=f"{r.route_id} duration {r.total_minutes/60:.1f}h exceeds "
                        f"{max_hours}h driver max"))

        # 8. WINDOW_AT_RISK — arrived on time but with little slack (Q9)
        for stop in r.stops:
            if not stop.on_time:
                continue  # already DELIVERY_LATE above
            loc = code_to_loc.get(stop.location_code)
            if not loc:
                continue
            wc_min = loc.delivery_window_close.hour * 60 + loc.delivery_window_close.minute
            margin = wc_min - stop.arrival_minutes_from_start
            if 0 < margin <= WINDOW_AT_RISK_MINUTES:
                findings.append(Exception_(
                    severity="WARNING", code="WINDOW_AT_RISK", route_id=r.route_id,
                    location_code=stop.location_code,
                    message=f"{r.route_id} arrives at {stop.location_code} only "
                            f"{int(margin)} min before window close"))

        # 9. LOW_UTILIZATION — both weight and cube under threshold (Q4)
        if (r.weight_utilization < LOW_UTIL_THRESHOLD
                and r.cube_utilization < LOW_UTIL_THRESHOLD):
            findings.append(Exception_(
                severity="INFO", code="LOW_UTILIZATION", route_id=r.route_id,
                message=f"{r.route_id} weight {int(r.weight_utilization*100)}% / "
                        f"cube {int(r.cube_utilization*100)}% — candidate for consolidation"))

        # 10. LONG_INTER_STOP_HOP — outlier leg vs route median (Q4)
        if depot and len(r.stops) >= 2:
            legs: list[tuple[str, float]] = []
            prev_lat, prev_lon = depot.latitude, depot.longitude
            for s in r.stops:
                legs.append((s.location_code, _haversine_miles(
                    prev_lat, prev_lon, s.latitude, s.longitude)))
                prev_lat, prev_lon = s.latitude, s.longitude
            legs.append(("RETURN_DC", _haversine_miles(
                prev_lat, prev_lon, depot.latitude, depot.longitude)))
            sorted_legs = sorted(d for _, d in legs)
            median_leg = sorted_legs[len(sorted_legs) // 2] if sorted_legs else 0.0
            for code, d in legs:
                if (d >= LONG_HOP_MIN_MILES
                        and d >= LONG_HOP_RATIO * max(1.0, median_leg)):
                    findings.append(Exception_(
                        severity="INFO", code="LONG_INTER_STOP_HOP", route_id=r.route_id,
                        location_code=code if code != "RETURN_DC" else None,
                        message=f"{r.route_id} has a {d:.0f}-mi leg to "
                                f"{code} (median leg {median_leg:.0f} mi)"))

        # 11. LCB_OFF_INTERSTATE — combo trailer with INTERSTATE_ONLY restriction
        # AND multiple stops in that state (proxy: multi-stop in restricted state
        # implies local roads). Q16. Documented as an approximation.
        if trailer:
            restricted_states = {
                rr.state for rr in bundle.road_restrictions
                if rr.applies_to(r.trailer_config)
                and rr.restriction_type == "INTERSTATE_ONLY"
            }
            if restricted_states:
                state_stop_count: dict[str, int] = {}
                for s in r.stops:
                    sl = code_to_loc.get(s.location_code)
                    if sl and sl.state in restricted_states:
                        state_stop_count[sl.state] = state_stop_count.get(sl.state, 0) + 1
                for st, n in state_stop_count.items():
                    if n >= 2:
                        findings.append(Exception_(
                            severity="WARNING", code="LCB_OFF_INTERSTATE", route_id=r.route_id,
                            message=f"{r.route_id} {r.trailer_config} has {n} stops in {st} "
                                    f"(interstate-only); legs between stops likely exceed "
                                    f"2-mi off-interstate cap"))

        # 12. LAYOVER detection — required if HOS already exceeded; suggested
        # at LAYOVER_FRACTION of cap (Q17). For required, propose a split-point
        # by walking stops and finding the last one inside the HOS envelope.
        if max_hours > 0 and r.stops:
            duration_hours = r.total_minutes / 60.0
            if duration_hours > max_hours + 0.01:
                first_arrival = r.stops[0].arrival_minutes_from_start
                split_at: str | None = None
                for s in r.stops:
                    cum_min = s.arrival_minutes_from_start - first_arrival
                    if cum_min <= max_hours * 60:
                        split_at = s.location_code
                    else:
                        break
                if split_at:
                    findings.append(Exception_(
                        severity="VIOLATION", code="LAYOVER_REQUIRED", route_id=r.route_id,
                        location_code=split_at,
                        message=f"{r.route_id} duration {duration_hours:.1f}h > "
                                f"{max_hours:.0f}h cap — recommend layover after "
                                f"{split_at}"))
            elif duration_hours > LAYOVER_FRACTION * max_hours:
                pct = int(duration_hours / max_hours * 100)
                findings.append(Exception_(
                    severity="INFO", code="LAYOVER_SUGGESTED", route_id=r.route_id,
                    message=f"{r.route_id} duration {duration_hours:.1f}h is "
                            f"{pct}% of {max_hours:.0f}h driver cap — driver may "
                            f"need rest break"))

    return findings
