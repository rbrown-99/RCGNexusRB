# Routing rules

## Cold-chain separation
Each route carries exactly one temperature group. The four groups are:
* `AMBIENT` — dry grocery, GM, HBC.
* `REFRIGERATED` — produce, dairy, deli (33–38°F).
* `FROZEN` — ice cream, frozen meals (–10 to 0°F).
* `MIXED` — multi-temp trailers (rare; only used for tiny rural stores).

The optimizer builds an independent VRP per temperature group from the same depot.

## Capacity stacking
A route is feasible only if **all three** caps hold:
1. Total weight ≤ effective state-aware weight cap.
2. Total cube ≤ effective cube cap (after stop-count degradation).
3. Stop count ≤ trailer's max stops.

If any cap is exceeded, the optimizer creates an additional route.

## Stop sequencing
Within a route, stops are sequenced to minimize total drive time while respecting each store's delivery window. The solver uses OR-Tools VRP with PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH.

## Backhauls and crossdock
Crossdock orders (`is_crossdock = true`) typically originate at supplier locations and are delivered to RDCs (e.g. Boise, Ogden). The current POC treats them as standard demand; future iteration would add pickup/delivery pairs.

## Cost objective
Total operating cost = `per_mile × total_miles + per_stop × stop_count + small fixed cost per dispatched vehicle`. Per-mile and per-stop rates come from `cost_proxies` in the constraint workbook.

## Naive baseline
For comparison the system computes "one truck per (store, temp-group), round-trip from DC". Savings vs naive is reported in every optimization result.
