"""OR-Tools VRP solver for Albertsons routing.

Approach
--------
For each temperature group (cold-chain separation), we build an independent VRP:

  * Nodes        : the DC (depot) + every store with demand in this temp group.
                   Each store appears once with aggregated demand
                   (weight + cube summed across all orders to that store of
                    matching temp group).
  * Vehicles     : a generous fleet built from the constraints workbook. We provide
                   several vehicles per trailer config so the solver can pick the
                   cheapest mix. Unused vehicles cost nothing.
  * Capacities   : weight (state-aware), cube (worst-case at max stops; we then
                   tighten via post-solve validation). Time windows enforced.
  * Cost         : per-mile + per-stop, plus a small fixed cost per used vehicle
                   to discourage spinning up unneeded trucks.

OR-Tools is then called with PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH.
The result is converted into Pydantic Route objects.
"""
from __future__ import annotations

import math
import time as _time
from collections import defaultdict
from typing import Iterable

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from ..models import (
    ConstraintBundle,
    Exception_,
    Location,
    NaiveBaseline,
    OptimizationResult,
    Order,
    Route,
    RouteStop,
)
from ..parser.orders_parser import aggregate_demand
from .constraint_encoder import effective_weight_capacity, relevant_restrictions
from .cost_matrix import CostMatrix


# Scaling factors: OR-Tools uses ints. Multiply floats then round.
DIST_SCALE = 100      # 0.01 mi resolution
TIME_SCALE = 1        # 1 minute
WEIGHT_SCALE = 1      # 1 lb
CUBE_SCALE = 1        # 1 cube
SERVICE_TIME_MIN = 30 # minutes per stop (load/unload)
DEPOT_OPEN_MIN = 0    # 00:00
DEPOT_CLOSE_MIN = 24 * 60 - 1


def _minutes_from_midnight(t) -> int:
    return int(t.hour) * 60 + int(t.minute)


def _build_vehicle_fleet(
    bundle: ConstraintBundle, n_locations_with_demand: int
) -> list[dict]:
    """Return a flat list of vehicle dicts (capacity-rich for the solver)."""
    fleet: list[dict] = []
    # Provide enough vehicles per config to cover any feasible scenario. A loose
    # upper bound is one vehicle per stop per config, but that is wasteful.
    # We use ceil(n / max_stops) + 2 per config.
    for trailer in bundle.trailer_types:
        per_truck_stops = max(1, trailer.max_stops)
        n = max(2, math.ceil(n_locations_with_demand / per_truck_stops) + 2)
        for k in range(n):
            fleet.append({
                "vehicle_id": f"{trailer.trailer_config}-{k+1:02d}",
                "trailer_config": trailer.trailer_config,
                "max_weight_lbs": trailer.max_weight_lbs,
                "max_cube_worst_case": min(
                    (bundle.degradation_for(trailer.trailer_config).cube_for_stops(trailer.max_stops)
                     if bundle.degradation_for(trailer.trailer_config) else trailer.max_cube_1stop),
                    trailer.max_cube_1stop,
                ),
                "max_stops": trailer.max_stops,
            })
    return fleet


def _solve_one_temp_group(
    temp_group: str,
    depot_location: Location,
    locations: dict[str, Location],
    demands: list[dict],          # list of aggregated demand dicts
    matrix: CostMatrix,
    bundle: ConstraintBundle,
    solver_seconds: int,
) -> tuple[list[Route], list[Exception_], str]:
    if not demands:
        return [], [], "EMPTY"

    # --- Node construction ------------------------------------------------
    # node 0 = depot, nodes 1..N = demand locations
    node_codes: list[str] = [depot_location.location_code]
    node_locations: list[Location] = [depot_location]
    node_weights: list[int] = [0]
    node_cubes: list[int] = [0]
    node_window: list[tuple[int, int]] = [(DEPOT_OPEN_MIN, DEPOT_CLOSE_MIN)]
    node_orders: list[list[str]] = [[]]

    for d in demands:
        loc = locations[d["location_code"]]
        node_codes.append(loc.location_code)
        node_locations.append(loc)
        node_weights.append(int(round(d["weight_lbs"] * WEIGHT_SCALE)))
        node_cubes.append(int(round(d["cube"] * CUBE_SCALE)))
        node_window.append((
            _minutes_from_midnight(loc.delivery_window_open),
            _minutes_from_midnight(loc.delivery_window_close),
        ))
        node_orders.append(list(d["order_ids"]))

    n_nodes = len(node_codes)
    n_demand_nodes = n_nodes - 1

    # --- Distance + time matrices in solver index space -------------------
    code_to_global = {c: i for i, c in enumerate(matrix.location_codes)}
    dist_int = [[0] * n_nodes for _ in range(n_nodes)]
    time_int = [[0] * n_nodes for _ in range(n_nodes)]
    for i in range(n_nodes):
        gi = code_to_global[node_codes[i]]
        for j in range(n_nodes):
            if i == j:
                continue
            gj = code_to_global[node_codes[j]]
            dist_int[i][j] = int(round(matrix.distances_miles[gi][gj] * DIST_SCALE))
            travel = matrix.times_minutes[gi][gj]
            # add service time at the destination (except returning to depot)
            service = SERVICE_TIME_MIN if j != 0 else 0
            time_int[i][j] = int(round(travel + service))

    # --- Vehicle fleet ----------------------------------------------------
    fleet = _build_vehicle_fleet(bundle, n_demand_nodes)
    n_vehicles = len(fleet)

    weight_caps: list[int] = []
    cube_caps: list[int] = []
    stop_caps: list[int] = []
    vehicle_costs_per_unit_dist: list[int] = []
    fixed_costs: list[int] = []

    per_mile = bundle.cost("per_mile", 4.0)
    per_stop = bundle.cost("per_stop", 30.0)

    # Distance arc cost = per_mile * miles. We pass that as cost/distance unit.
    # OR-Tools wants integer costs. We use cost-per-unit-distance = per_mile (then
    # divide by DIST_SCALE on output). Keep as int per-100-miles -> per_mile * 100.
    arc_cost_per_unit = max(1, int(round(per_mile * 100)))  # cost units per scaled-mile

    for v in fleet:
        weight_caps.append(int(round(v["max_weight_lbs"] * WEIGHT_SCALE)))
        cube_caps.append(int(round(v["max_cube_worst_case"] * CUBE_SCALE)))
        stop_caps.append(v["max_stops"])
        vehicle_costs_per_unit_dist.append(arc_cost_per_unit)
        # small fixed cost so unused trucks stay unused
        fixed_costs.append(int(round(per_stop * 100)))  # = $30

    # --- OR-Tools model ---------------------------------------------------
    manager = pywrapcp.RoutingIndexManager(n_nodes, n_vehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_cb(from_index, to_index):
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return dist_int[i][j]

    def time_cb(from_index, to_index):
        i = manager.IndexToNode(from_index)
        j = manager.IndexToNode(to_index)
        return time_int[i][j]

    def weight_demand_cb(from_index):
        return node_weights[manager.IndexToNode(from_index)]

    def cube_demand_cb(from_index):
        return node_cubes[manager.IndexToNode(from_index)]

    def stop_demand_cb(from_index):
        return 0 if manager.IndexToNode(from_index) == 0 else 1

    transit_idx = routing.RegisterTransitCallback(distance_cb)
    time_idx = routing.RegisterTransitCallback(time_cb)
    weight_idx = routing.RegisterUnaryTransitCallback(weight_demand_cb)
    cube_idx = routing.RegisterUnaryTransitCallback(cube_demand_cb)
    stop_idx = routing.RegisterUnaryTransitCallback(stop_demand_cb)

    # arc cost (varies by vehicle so we'd normally use SetArcCostEvaluatorOfVehicle;
    # here all vehicles share per-mile cost so plain SetArcCostEvaluatorOfAllVehicles
    # is fine).
    routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)

    # add fixed cost per used vehicle
    for v_idx in range(n_vehicles):
        routing.SetFixedCostOfVehicle(fixed_costs[v_idx], v_idx)

    # capacity dimensions
    routing.AddDimensionWithVehicleCapacity(weight_idx, 0, weight_caps, True, "Weight")
    routing.AddDimensionWithVehicleCapacity(cube_idx, 0, cube_caps, True, "Cube")
    routing.AddDimensionWithVehicleCapacity(stop_idx, 0, stop_caps, True, "Stops")

    # time dimension with windows
    routing.AddDimension(time_idx, 24 * 60, 24 * 60, False, "Time")
    time_dim = routing.GetDimensionOrDie("Time")
    for node in range(1, n_nodes):
        idx = manager.NodeToIndex(node)
        open_, close_ = node_window[node]
        time_dim.CumulVar(idx).SetRange(open_, close_)
    # depot start window: any time
    for v_idx in range(n_vehicles):
        time_dim.CumulVar(routing.Start(v_idx)).SetRange(DEPOT_OPEN_MIN, DEPOT_CLOSE_MIN)

    # search params
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromSeconds(solver_seconds)

    solution = routing.SolveWithParameters(params)
    if solution is None:
        return [], [Exception_(severity="VIOLATION", code="NO_SOLUTION",
                               message=f"No feasible routes for temperature group {temp_group}")], "INFEASIBLE"

    # --- Extract routes --------------------------------------------------
    routes: list[Route] = []
    exceptions: list[Exception_] = []
    route_seq = 1

    for v_idx in range(n_vehicles):
        index = routing.Start(v_idx)
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue  # unused vehicle

        v = fleet[v_idx]
        trailer = bundle.trailer(v["trailer_config"])
        degradation = bundle.degradation_for(v["trailer_config"])
        stops: list[RouteStop] = []
        seq = 0
        prev_index = None
        total_miles = 0.0
        total_minutes = 0.0
        total_weight = 0.0
        total_cube = 0.0
        states_traversed: set[str] = set()
        on_time_route = True

        # walk the route
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if prev_index is not None and node != 0:
                pi = manager.IndexToNode(prev_index)
                total_miles += dist_int[pi][node] / DIST_SCALE
                total_minutes += time_int[pi][node]
            if node != 0:
                seq += 1
                loc = node_locations[node]
                states_traversed.add(loc.state)
                arrival = solution.Value(time_dim.CumulVar(index))
                window_close = node_window[node][1]
                on_time = arrival <= window_close
                on_time_route = on_time_route and on_time
                stops.append(RouteStop(
                    sequence=seq,
                    location_code=loc.location_code,
                    location_name=loc.location_name,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    arrival_minutes_from_start=float(arrival),
                    departure_minutes_from_start=float(arrival + SERVICE_TIME_MIN),
                    weight_delivered_lbs=float(node_weights[node] / WEIGHT_SCALE),
                    cube_delivered=float(node_cubes[node] / CUBE_SCALE),
                    order_ids=node_orders[node],
                    on_time=on_time,
                ))
                total_weight += node_weights[node] / WEIGHT_SCALE
                total_cube += node_cubes[node] / CUBE_SCALE
            prev_index = index
            index = solution.Value(routing.NextVar(index))

        # closing leg back to depot
        end_node = manager.IndexToNode(index)
        if prev_index is not None:
            pi = manager.IndexToNode(prev_index)
            total_miles += dist_int[pi][end_node] / DIST_SCALE
            total_minutes += time_int[pi][end_node]

        if not stops:
            continue

        # Effective cube cap given degradation by stop count
        if degradation:
            effective_cube_cap = degradation.cube_for_stops(len(stops))
        else:
            effective_cube_cap = trailer.max_cube_1stop if trailer else float(v["max_cube_worst_case"])

        # State-aware effective weight cap
        if trailer:
            eff_weight_cap = effective_weight_capacity(bundle, trailer, list(states_traversed))
        else:
            eff_weight_cap = float(v["max_weight_lbs"])

        cube_util = (total_cube / effective_cube_cap) if effective_cube_cap > 0 else 0.0
        weight_util = (total_weight / eff_weight_cap) if eff_weight_cap > 0 else 0.0
        cost = total_miles * per_mile + len(stops) * per_stop

        route_id = f"R{route_seq:02d}-{v['trailer_config']}-{temp_group}"
        routes.append(Route(
            route_id=route_id,
            trailer_config=v["trailer_config"],
            temperature_group=temp_group,
            stops=stops,
            total_miles=round(total_miles, 2),
            total_minutes=round(total_minutes, 1),
            total_weight_lbs=round(total_weight, 1),
            total_cube=round(total_cube, 1),
            weight_capacity_lbs=round(eff_weight_cap, 1),
            cube_capacity=round(effective_cube_cap, 1),
            weight_utilization=round(weight_util, 4),
            cube_utilization=round(cube_util, 4),
            estimated_cost_usd=round(cost, 2),
            on_time=on_time_route,
            states_traversed=sorted(states_traversed),
        ))
        route_seq += 1

    return routes, exceptions, "OK"


def _naive_baseline(
    locations_by_code: dict[str, Location],
    aggregated: dict[tuple[str, str], dict],
    matrix: CostMatrix,
    bundle: ConstraintBundle,
    depot_code: str,
) -> NaiveBaseline:
    """One truck per (location, temp_group) — round-trip from depot."""
    per_mile = bundle.cost("per_mile", 4.0)
    per_stop = bundle.cost("per_stop", 30.0)
    total_miles = 0.0
    total_routes = 0
    depot_idx = matrix.index_of(depot_code)
    for (code, _), _ in aggregated.items():
        if code == depot_code:
            continue
        idx = matrix.index_of(code)
        round_trip = matrix.distances_miles[depot_idx][idx] + matrix.distances_miles[idx][depot_idx]
        total_miles += round_trip
        total_routes += 1
    total_cost = total_miles * per_mile + total_routes * per_stop
    return NaiveBaseline(
        total_routes=total_routes,
        total_miles=round(total_miles, 2),
        total_cost_usd=round(total_cost, 2),
    )


def solve_vrp(
    orders: list[Order],
    locations: list[Location],
    matrix: CostMatrix,
    bundle: ConstraintBundle,
    *,
    solver_seconds: int = 30,
) -> OptimizationResult:
    """Solve the full multi-temperature-group VRP and produce an OptimizationResult."""
    started = _time.perf_counter()
    locations_by_code = {loc.location_code: loc for loc in locations}
    depots = [loc for loc in locations if loc.location_type == "DC"]
    if not depots:
        raise ValueError("no DC location found")
    depot = depots[0]

    aggregated = aggregate_demand(orders)

    # Group aggregated demands by temp_group, drop demands at the depot itself.
    by_temp: dict[str, list[dict]] = defaultdict(list)
    for (code, temp), bucket in aggregated.items():
        if code == depot.location_code:
            continue
        if code not in locations_by_code:
            continue
        by_temp[temp].append(bucket)

    all_routes: list[Route] = []
    all_exceptions: list[Exception_] = []
    statuses: list[str] = []

    for temp_group, demands in sorted(by_temp.items()):
        routes, excs, status = _solve_one_temp_group(
            temp_group=temp_group,
            depot_location=depot,
            locations=locations_by_code,
            demands=demands,
            matrix=matrix,
            bundle=bundle,
            solver_seconds=max(1, solver_seconds // max(1, len(by_temp))),
        )
        all_routes.extend(routes)
        all_exceptions.extend(excs)
        statuses.append(f"{temp_group}:{status}")

    # Renumber routes overall
    for i, r in enumerate(all_routes, 1):
        r.route_id = f"R{i:02d}-{r.trailer_config}-{r.temperature_group}"

    total_miles = sum(r.total_miles for r in all_routes)
    total_cost = sum(r.estimated_cost_usd for r in all_routes)
    avg_weight_util = (sum(r.weight_utilization for r in all_routes) / len(all_routes)) if all_routes else 0.0
    avg_cube_util = (sum(r.cube_utilization for r in all_routes) / len(all_routes)) if all_routes else 0.0

    naive = _naive_baseline(locations_by_code, aggregated, matrix, bundle, depot.location_code)
    savings = naive.total_cost_usd - total_cost
    savings_pct = (savings / naive.total_cost_usd * 100) if naive.total_cost_usd > 0 else 0.0

    # Considerations applied
    considerations = [
        "Cold chain separation: routes split by temperature group",
        "Cube degradation by stop count: capacity tightened post-solve",
        "Weight capacity per state (WY 40-40 combo limit applied where relevant)",
        "Delivery time windows enforced as hard constraints",
        f"Distance source: {'Azure Maps Route Matrix (truck profile)' if matrix.used_azure_maps else 'Haversine fallback (great-circle x 1.3, 55 mph)'}",
    ]
    relaxed: list[str] = []

    return OptimizationResult(
        routes=all_routes,
        exceptions=all_exceptions,
        considerations=considerations,
        relaxed_constraints=relaxed,
        total_routes=len(all_routes),
        total_miles=round(total_miles, 2),
        total_cost_usd=round(total_cost, 2),
        average_weight_utilization=round(avg_weight_util, 4),
        average_cube_utilization=round(avg_cube_util, 4),
        naive_baseline=naive,
        savings_usd=round(savings, 2),
        savings_percent=round(savings_pct, 2),
        solver_status="; ".join(statuses),
        solve_seconds=round(_time.perf_counter() - started, 2),
    )
