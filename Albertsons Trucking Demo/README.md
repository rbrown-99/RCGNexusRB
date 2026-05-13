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
| POST | `/api/optimize-from-samples` | One-call demo: parses bundled `sample_data/` and optimizes |
| POST | `/api/validate/{session_id}` | Re-run validator on a session's routes |
| POST | `/api/reoptimize/{session_id}` | What-if: drop orders/locations/trailers, add a note |
| POST | `/api/compare?session_a=&session_b=` | Side-by-side delta of two sessions |
| GET  | `/api/explain/{session_id}/{route_id}` | Structured rationale for a single route |
| GET  | `/healthz` | Liveness |

## Agent layer

The frontend ships with a **rules-based fallback agent** (`frontend/src/services/agentClient.ts`) that translates natural language ("what if we lose 45-45 trailers", "drop ALB-MT-MISA", "explain R03-…", "validate") into the API calls above. To swap in a real Foundry hosted agent, replace `agentClient.ask()` with a Foundry SDK call and load `agent/agent_config.yaml` + the grounding docs into your Foundry project.

## Environment variables

See `.env.example`. Copy to `.env` and fill in (all optional for local dev).

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
