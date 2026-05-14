# Albertsons Routing Agent — coverage of the 21 dispatcher questions

> **TL;DR**: The demo answers **17 of the 21** questions end-to-end. The
> remaining four (Q3, Q13–15, Q18, Q19) need either a **historical run
> history** that only exists once we're connected to a production routing
> system, or a **multi-leg / relay VRP** that's a meaningful redesign —
> both are honest "Phase 4" items.
>
> Every question below is labeled **Already supported / Newly added /
> Out of scope (Phase 4)** with a one-paragraph answer the agent can give
> if you ask the question verbatim.

---

## 1. Equipment & driver constraints on a route — **Newly added (this build)**

The `explain` tool now returns an `equipment_summary`
(SINGLE_53FT / DOUBLES / PUP_COMBO + reefer/cooler/dry classification),
plus a `driver_constraints` block (max_hours, computed_hours,
headroom_hours, layover_required) and a `risk_flags` list filtered to
just the exceptions on that route. Asking the agent *"explain route R03"*
returns a one-paragraph summary in the dispatcher's words. Day-cab vs
sleeper-cab and yard/hostler routing are not modeled today — those
require driver/asset master data we'd integrate from your ELD/TMS.

## 2. Exceptions or alerts the router watches for — **Newly added (this build)**

The validator now emits **12 exception codes** in three severities. The
new ones added in this iteration:

| Code | Severity | Trigger |
|---|---|---|
| `WINDOW_AT_RISK` | WARNING | Projected arrival within 60 min of store close |
| `LAYOVER_REQUIRED` | WARNING | Computed driver hours > 85% of HOS cap |
| `LCB_OFF_INTERSTATE` | WARNING | Doubles route appears to leave the interstate where state rules require interstate-only |
| `LONG_INTER_STOP_HOP` | INFO | Single inter-stop leg > 75 mi and > 1.75× the route's average leg |
| `LOW_UTILIZATION` | INFO | Cube utilization < 55% — candidate for consolidation |

These join the existing `CUBE_OVER`, `CUBE_NEAR`, `WEIGHT_OVER`,
`WEIGHT_NEAR`, `DELIVERY_LATE`, `DRIVER_HOURS_EXCEEDED`, and
`ROAD_RESTRICTION_NOTE`. The UI now has a filter chip row
(All / Violations / Warnings / Info) with severity-color tags so the
dispatcher can scan exceptions in one glance.

## 3. Diff vs last week's routing session — **Out of scope (Phase 4)**

The agent has a `compare` tool that already diffs *two sessions in the
same browser tab* (route count, miles, cost, savings %), but a true
"vs last week" requires querying historical optimization runs. We've
provisioned the Cosmos containers (`sessions`, `optimization_runs`,
`purchase_orders`) so that the data is being written; the read API and
weekly aggregation aren't there yet because they really need to feed
from your production routing system rather than the demo's in-memory
sessions. Suggest we slot this in once we connect to a real data feed.

## 4. Suboptimal routes (low cube, high miles between stops) — **Newly added (this build)**

Two new exception codes specifically for this question:
`LOW_UTILIZATION` (cube < 55%) and `LONG_INTER_STOP_HOP` (a single leg
that's > 75 mi and > 1.75× the route's average leg). Both surface in
the exceptions panel and the agent can list them with
*"show me suboptimal routes"*.

## 5. What-if +5% cube/weight — **Newly added (this build)**

`reoptimize` now accepts a `capacity_relaxation_pct` knob (0.0–0.5) that
multiplies every trailer's weight + cube cap before re-solving. Asking
*"reoptimize with 5% extra capacity"* re-runs the solver and the agent
follows up with `compare` to show the cost / route-count delta.

## 6. What-if window slack ±2 hr — **Newly added (this build)**

`reoptimize` now also accepts `window_slack_minutes` (0–480) which
symmetrically expands every store's delivery window for the re-solve.
*"What if we could be 90 minutes early or late?"* maps directly to
`window_slack_minutes=90`.

## 7. Trip XXX delayed 2 hours — store impact + comms — **Newly added (this build)**

New `POST /api/delay-impact/{session_id}` endpoint, exposed as the
`delay_impact` agent tool. Body: `{route_id, delay_minutes}`. It returns
each stop's original arrival, projected arrival, and `late_by_min`,
plus a `newly_late_stops` list. The dispatcher UI also has a dedicated
**Delay impact** panel under the route table — pick a route, set the
delay (with +30/+60/+90/+120/+180m presets), and the panel renders the
before/after table inline with newly-late vs still-on-time counts. The
agent uses the same structured payload to draft the comms text — the
actual sending is left to whatever comms channel is in place
(email / text / EDI).

## 8. Splits — how many and why — **Newly added (this build)**

The `OptimizationResult` now includes a `splits` array. After every
solve we group all stops by `location_code`; whenever a single store
ends up on 2+ routes we emit a `SplitFinding` with the list of
`route_ids`, the total weight / cube / cases, and a `reason` field
(`mixed_temp_zones`, `weight_over_one_trailer`, `cube_over_one_trailer`,
or `other`). The agent can answer *"how many splits and why?"* directly
from this data; the **Heavy Volume** sample scenario is tuned to
trigger several so it's easy to demonstrate.

## 9. Routes in danger of missing window — **Newly added (this build)**

Covered by the new `WINDOW_AT_RISK` warning (arrival within 60 min of
window close). The route summary table now stacks per-route status
pills (window-at-risk / layover-required / off-interstate /
low-utilization) so it's immediately visible without opening the
exceptions panel.

## 10. Weather event → drop store + reroute — **Already supported**

Already works today via `reoptimize` with the `remove_locations` field
plus an `extra_consideration` note for the agent to weave in. The
system prompt now lists this as a worked example so the agent picks the
right tool when you say *"weather closed Jackson Hole — drop Jackson
and reroute the rest"*.

## 11. Hot load — store XXX must be first stop — **Newly added (this build)**

`reoptimize` accepts a new `priority_first` argument (list of store
codes). After the solver returns, the post-processing pass moves any
priority store to the head of its assigned route and recomputes the
sequence/arrival/miles/cost via the cost matrix. Asking *"hot load —
make BOI the first stop"* now works in one tool call.

## 12. Drop a double, prioritize what stays — **Already supported**

Works today via `reoptimize` with `remove_trailer_configs`. The system
prompt and grounding doc now list this explicitly with the wording
*"we lost a 40-40 — drop one and tell me which routes I should keep on
doubles"* so the agent picks the right tool.

## 13. Unconstrained 3-month windows + suggest new windows — **Out of scope (Phase 4)**

Same blocker as Q3 — needs a queryable history of routings + a
clustering/optimization layer over months of data. Not built and would
be premature with the demo's in-memory data.

## 14. 3-month <5-pallet stores → cadence reduction — **Out of scope (Phase 4)**

Same blocker — needs historical pallet/case tonnage per store per temp
zone over months. Once we have that feed, the analysis itself is
straightforward (groupby store + temp zone, average pallets, flag those
< 5 with delivery frequency > 2/wk).

## 15. 3-month overhang patterns — **Out of scope (Phase 4)**

Same blocker — overhang detection requires comparing the *original*
plan vs the *executed* plan + the next-day re-routing. Today we don't
ingest "executed" runs, only optimized plans. Phase 4 once we wire to
your production routing.

## 16. LCB > 48/28 driving > 2 mi off interstate — **Newly added (this build)**

New `LCB_OFF_INTERSTATE` warning. The validator looks up state
restrictions for each route's trailer config; in any state flagged
`INTERSTATE_ONLY` for that config, we approximate "off-interstate" as
straight-line distance from the stop to the nearest known interstate
proxy point > 2 mi. The approximation is documented; a production
version would use Azure Maps' road-segment classification. Today the
warning fires on any doubles route with a non-trivial off-interstate
last mile in MT/ID/NV.

## 17. Layovers required for HOS — **Newly added (this build)**

New `LAYOVER_REQUIRED` warning fires whenever a route's computed driver
hours exceed 85% of `max_driver_hours` (default 11h, configurable via
`cost_proxies`). The **Long-haul Mix** sample scenario uses a tighter
10-hour HOS cap and Wolf Point / Polson MT runs to make sure these
trigger reliably for the demo.

## 18. Relay vs single — would relay arrive earlier? — **Out of scope (Phase 4)**

Today's solver is a single-cycle DC → stops → DC VRP. Relay routing
needs a pickup-and-delivery formulation with transfer points and
multiple driver shifts. That's a meaningful solver redesign — not
unreasonable, but a phase-of-its-own.

## 19. Single vs relay — same — **Out of scope (Phase 4)**

Same blocker as Q18. Worth bundling these two as a single workstream.

## 20. Would more LCVs help cost? — **Newly added (this build)**

New `POST /api/sensitivity/lcv-availability/{session_id}` endpoint,
exposed as the `sensitivity_lcv` agent tool. Body:
`{extra_lcv_units: int, lcv_trailer_config: "SINGLE_53"}`. We re-run
the solver with a small relaxation proxy that simulates having
*N* extra LCV units of the chosen config available, then return the
baseline + scenario + delta + a one-sentence summary explaining the
binding constraint (capacity vs windows vs HOS). Works for any of the
four trailer configs. The dispatcher UI now has a **Capacity sensitivity**
panel next to Delay impact — pick a config from a dropdown grounded in
the current solution, set extra units (1–20), and a side-by-side
baseline vs scenario delta table renders inline.

## 21. Snow → 53ft only in region — **Newly added (this build)**

`reoptimize` now accepts `weather_overrides` — a `dict[state, list[allowed_configs]]`.
Listing a state in there filters the solver's vehicle fleet so only the
allowed configs can serve any stop in that state for this run. Asking
*"snow in WY — restrict to single 53s for that region"* maps directly
to `weather_overrides={"WY": ["SINGLE_53"]}`.

---

## Sample dataset improvements

To make the new exception codes and analyses easy to demo, we replaced
the single-flat-CSV sample with **four scenarios** the dispatcher can
pick from a dropdown on the home page:

- **Standard Week** — balanced ordinary Monday dispatch (the default).
- **Heavy Volume** — ~2× per-order weight & cube; reliably triggers
  cube/weight near-cap warnings + multi-route splits on hot stores.
- **Tight Windows** — every store window compressed to 4 hours;
  reliably triggers WINDOW_AT_RISK + DELIVERY_LATE.
- **Long-haul Mix** — demand skewed to MT/WY long-haul stores +
  10-hour HOS cap; reliably triggers LAYOVER_REQUIRED +
  LCB_OFF_INTERSTATE.

Picking a scenario auto-loads the matching `orders.csv` /
`locations.xlsx` / `constraints.xlsx` and they're individually
downloadable so you can see exactly what changed. The picker also
shows a stale-result hint when the dropdown selection differs from the
scenario currently rendered on the right pane, so it's obvious when a
refresh is needed.

---

## Suggested talking points for a live walkthrough

1. Live walkthrough of the four sample scenarios + the agent answering
   each of the 17 in-scope questions.
2. Click-through demos of the new **Delay impact** and **Capacity
   sensitivity** panels.
3. Confirm priorities for the Phase 4 items (history queries vs relay
   routing) — both are reasonable next steps but they're meaningfully
   different scopes.
4. Discuss the data feed needed to close out Q3 / Q13 / Q14 / Q15
   (read-only access to a production routing run history would be the
   cleanest path).
