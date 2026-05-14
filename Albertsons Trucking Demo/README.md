# Albertsons Truck Routing Optimization Agent

POC for an agent-driven truck routing optimizer for Albertsons Companies' Salt Lake City distribution center.

## Architecture

Three tiers:

1. **Frontend** — Azure Static Web App (React + TypeScript + Vite) — file upload, chat, route map, summary tables.
2. **Backend** — Python FastAPI service — file parsing, Azure Maps Route Matrix, OR-Tools VRP solver.
3. **Agent** — Azure AI Foundry agent — domain-grounded conversational layer that orchestrates backend tools.

```
Albertsons Trucking Demo/
├── sample_data/        Synthetic test files (orders, constraints, locations)
├── scripts/            Data generators and helpers
├── backend/            Python FastAPI + OR-Tools service
├── agent/              Foundry agent config, grounding docs, tool definitions
├── frontend/           React + TypeScript Static Web App
└── infra/              Bicep IaC
```

## Quickstart (local dev, no Azure required)

### 1. Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn src.main:app --reload --port 8000
```

The backend uses the **haversine fallback** for distances when `AZURE_MAPS_KEY` is not set in `.env`.

### 2. Regenerate sample data (optional — already committed)
```powershell
python scripts\generate_sample_data.py
```

### 3. Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### 4. Smoke-test the optimizer end-to-end
```powershell
curl -X POST http://localhost:8000/api/optimize-from-samples
```

Or run the bundled smoke script (no server required):
```powershell
.\backend\.venv\Scripts\python.exe scripts\smoke_test.py
```

## API surface

All endpoints are under `/api`. CORS allows `http://localhost:5173` by default.

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/parse` | Multipart upload (orders, locations, constraints) → returns `session_id` |
| POST | `/api/optimize` | Run VRP for an existing `session_id` *or* upload three files inline |
| POST | `/api/optimize-from-samples?scenario=...` | One-call demo: parses bundled scenario data and optimizes |
| POST | `/api/validate/{session_id}` | Re-run validator on a session's routes (12 exception codes) |
| POST | `/api/reoptimize/{session_id}` | What-if: drop orders/locations/trailers, plus 4 knobs: `capacity_relaxation_pct`, `window_slack_minutes`, `priority_first[]`, `weather_overrides{}` |
| POST | `/api/compare?session_a=&session_b=` | Side-by-side delta of two sessions |
| POST | `/api/delay-impact/{session_id}` | Project a manual delay through a route, list newly-late stops (no re-solve) |
| POST | `/api/sensitivity/lcv-availability/{session_id}` | Re-solve with extra units of a trailer config; return baseline vs scenario delta |
| GET  | `/api/explain/{session_id}/{route_id}` | Equipment summary + driver constraints + risk flags + plain-English narrative |
| GET  | `/api/samples/` | Catalog of sample scenarios |
| GET  | `/api/samples/{key}?scenario=...` | Download a single sample file (`orders` / `locations` / `constraints`) |
| GET  | `/healthz` | Liveness |

The backend also boots an **MCP server** (FastMCP, streamable-HTTP) at `/mcp`
exposing the same 9 endpoints as 10 agent tools (`parse`, `optimize`, `validate`,
`reoptimize`, `compare`, `explain`, `delay_impact`, `sensitivity_lcv`,
`get_samples`, `get_session`). Drop in to any MCP-aware agent runtime
(Foundry, Claude Desktop, Cursor, etc.).

## Sample scenarios

The demo ships four scenarios under `sample_data/<key>/{orders.csv, locations.xlsx, constraints.xlsx}`,
each tuned to trigger a different mix of exceptions. Pick one from the
**Scenario** dropdown on the home page; download the per-scenario inputs from
the same panel.

| Key | Description | Notable exceptions |
| --- | --- | --- |
| `standard_week` | Balanced ordinary Monday dispatch (~70 orders) | Mostly clean — light WINDOW_AT_RISK / LOW_UTILIZATION |
| `heavy_volume`  | ~110 orders × ~2 cube/weight | CUBE_NEAR/OVER, WEIGHT_NEAR/OVER, multi-route splits |
| `tight_windows` | ~100 orders, store windows compressed to 4 hours | WINDOW_AT_RISK, DELIVERY_LATE |
| `long_haul_mix` | ~90 orders skewed to MT/WY + 10-hour HOS cap | LAYOVER_REQUIRED, LCB_OFF_INTERSTATE, LONG_INTER_STOP_HOP |

If the dropdown selection differs from the scenario currently rendered on the
right pane, the picker shows a stale-result hint so you know to re-run.

The `OptimizationResult` carries a `splits[]` block when any single store ends
up on 2+ routes, classified as `mixed_temp_zones` / `weight_over_one_trailer` /
`cube_over_one_trailer`.

## Agent layer

The frontend ships with a **rules-based fallback agent** (`frontend/src/services/agentClient.ts`) that translates natural language ("what if we lose 45-45 trailers", "drop ALB-MT-MISA", "explain R03-…", "validate") into the API calls above. To swap in a real Foundry hosted agent, replace `agentClient.ask()` with a Foundry SDK call and load `agent/agent_config.yaml` + the grounding docs into your Foundry project.

The dispatcher pane also surfaces two **click-through what-if panels** below the
exceptions panel that hit the same backend endpoints without going through the
chat:

- **Delay impact** — pick a route + delay (presets +30 / +60 / +90 / +120 / +180 m), see the projected per-stop arrival table and which stops newly miss their window.
- **Capacity sensitivity** — pick a trailer config from a dropdown grounded in the current solution + extra units (1–20), re-solve and see the baseline vs scenario delta on cost, miles, and route count.

## Environment variables

See `.env.example`. Copy to `.env` and fill in (all optional for local dev).

## Customer Q&A coverage

[docs/customer-questions-coverage.md](docs/customer-questions-coverage.md)
maps the demo's capabilities against the 21 dispatcher questions the agent
should be able to answer. 17 of 21 are addressed end-to-end; the remaining
four are tagged Phase 4 with their data-feed / solver-redesign blockers.

## Roadmap — Phase 4 (post-demo)

The four questions deliberately scoped out of this build all need
infrastructure beyond the demo's scope:

- **Q3 — diff vs last week's routing session.** Cosmos containers exist
  (`sessions`, `optimization_runs`, `purchase_orders` per
  `backend/src/persistence.py`) but there's no read API and no time-series
  aggregation. Real version would feed from a production routing system.
- **Q13 — unconstrained 3-month windows analysis.** Same blocker — needs
  queryable history of past optimization runs + a clustering layer.
- **Q14 — 3-month <5-pallet cadence reduction.** Same blocker — needs
  historical pallet/case tonnage per store per temp zone over months.
- **Q15 — 3-month overhang patterns.** Same blocker, plus needs to ingest
  *executed* runs (not just optimized plans) for plan-vs-actual comparison.
- **Q18 / Q19 — relay vs single dispatch.** Today's solver is a single-cycle
  DC → stops → DC VRP. Relay routing requires a pickup-and-delivery
  formulation with transfer points and multiple driver shifts — a meaningful
  solver redesign.

## Success criteria

- Upload 3 sample files → 8–12 optimized routes within 60 s.
- Routes respect weight, cube-with-degradation, delivery windows, road restrictions, cold chain.
- Optimized total cost is lower than the naive (one-truck-per-store) baseline.
- Routes rendered on a map with stop sequencing.
- Chat supports "what if" questions and re-optimization.
- Runs fully locally with the haversine fallback.

## Phased delivery

- **Phase 1 (this build):** POC, file upload, SLC DC, AI vs naive comparison.
- **Phase 2:** Real-time TMS (Prospero/Cosmos) integration, feedback loop, weather.
- **Phase 3:** All 18 DCs, driver scheduling, load placement, end-to-end automation.
