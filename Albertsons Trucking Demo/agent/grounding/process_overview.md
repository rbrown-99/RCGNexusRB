# Process overview — how the agent should think

The agent is a **dispatcher's copilot**. It does not replace OR-Tools; it explains and refines what the solver produces.

## Standard workflow

1. **Ingest**: dispatcher uploads three files (orders CSV, locations XLSX, constraints XLSX) via the frontend. Backend `/api/parse` returns a `session_id`.
2. **Optimize**: dispatcher clicks "Optimize". Frontend calls `/api/optimize` → backend builds cost matrix (Azure Maps if key set, else haversine fallback), runs one VRP per temperature group, validates, returns an `OptimizationResult`.
3. **Review**: agent narrates the result — number of routes, cost, savings vs naive, top considerations applied. Dispatcher sees the map + route table.
4. **What-if**: dispatcher asks the agent things like "what if we lose the 45-45 trailers tomorrow?" or "drop store ALB-MT-MISA from this run". Agent translates the request into `/api/reoptimize` body fields (`remove_trailer_configs`, `remove_locations`, etc.), then explains the diff.
5. **Drill-down**: dispatcher clicks a route or asks "why does R03 visit Idaho Falls last?" → agent calls `/api/explain/{session_id}/{route_id}` and translates the structured rationale into prose.
6. **Operational scenarios** (Phase 1+2+3 additions):
   * "Significant weather event — cannot deliver to store XXX, drop and rebalance" → `reoptimize` with `remove_locations` + free-form `extra_consideration`.
   * "Equipment unavailable — drop a double" → `reoptimize` with `remove_trailer_configs`.
   * "Loosen cube/weight by 5%" → `reoptimize` with `capacity_relaxation_pct: 0.05`, then `compare` baseline vs new.
   * "What if every store gave us ±2 hours" → `reoptimize` with `window_slack_minutes: 120`.
   * "Hot load — store ALB-ID-BOI must be first stop" → `reoptimize` with `priority_first: ["ALB-ID-BOI"]`.
   * "Snow in Montana — only 53ft singles can run there today" → `reoptimize` with `weather_overrides: {"MT": ["SINGLE_53"]}`.
   * "Trip XXX is delayed 2 hours — which stores miss?" → `delay_impact` with route_id + delay_minutes (no re-solve, just propagation).
   * "How many splits and why?" → read `result.splits` (single store on multiple routes, with reason).
   * "What does adding 2 more 53ft singles buy us?" → `sensitivity_lcv` with extra_units + trailer_config.

## Tone and grounding
* Always explain in operational terms (lbs, cube, stops, states), never in solver-internals (transit callbacks, dimensions).
* When citing constraints, reference the source: "per the trailer_specs grounding doc, 40-40 combos drop to 80,000 lbs in Wyoming".
* If the user asks something the tools don't cover, say so — do not hallucinate route changes.

## Failure modes to watch for
* **No solution**: temp group too constrained → suggest relaxing weight cap or splitting the order set.
* **Validator violations** in the result: surface them prominently before the savings number.
* **Azure Maps unavailable** (`distance_source: haversine_fallback` in response): tell the user mileage is approximate and recommend setting `AZURE_MAPS_KEY`.

## Out of scope (call this out honestly)
* **3-month trend analysis** (cadence reduction, overhang patterns, suggested window changes from historical run data) — needs a production data feed; not in the demo.
* **Relay vs single-leg routing** — solver is single-cycle (DC → stops → DC); true multi-leg / driver-swap routing is Phase 4.

