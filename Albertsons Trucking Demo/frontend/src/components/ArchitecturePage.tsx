import MermaidDiagram from './MermaidDiagram';

const ARCH_DIAGRAM = `
flowchart LR
  classDef user fill:#fff,stroke:#1f2330,stroke-width:2px,color:#1f2330
  classDef ui fill:#fdf2f1,stroke:#d52b1e,stroke-width:2px,color:#1f2330
  classDef api fill:#fef9e6,stroke:#a86c00,stroke-width:2px,color:#1f2330
  classDef solver fill:#e6f4ea,stroke:#2a8a2a,stroke-width:2px,color:#1f2330
  classDef ext fill:#eef5fc,stroke:#4a90e2,stroke-width:2px,color:#1f2330
  classDef store fill:#f3eee2,stroke:#7a6f4a,stroke-width:2px,color:#1f2330
  classDef mcp fill:#f0e6ff,stroke:#6c3fb5,stroke-width:2px,color:#1f2330

  U([Dispatcher / Business User]):::user

  subgraph FE["Frontend — React + TypeScript + Vite"]
    direction TB
    UI1[Scenario Picker + Samples<br/>+ stale-result hint]:::ui
    UI2[File Upload]:::ui
    UI3[Chat Copilot]:::ui
    UI4[Map · KPIs · Tables · Exception Filters]:::ui
    UI5[Delay Impact Panel<br/>Sensitivity Panel]:::ui
  end

  subgraph BE["Backend — FastAPI on Container Apps"]
    direction TB
    API1["/api/parse"]:::api
    API2["/api/optimize"]:::api
    API3["/api/validate"]:::api
    API4["/api/reoptimize"]:::api
    API5["/api/explain"]:::api
    API6["/api/compare"]:::api
    API7["/api/delay-impact"]:::api
    API8["/api/sensitivity/lcv-availability"]:::api
    API9["/api/samples?scenario=..."]:::api
  end

  subgraph CORE["Core engines"]
    direction TB
    P[Pandas / openpyxl<br/>parsers]:::solver
    S[OR-Tools Routing<br/>multi-temp VRP]:::solver
    V[Route Validator<br/>12 exception codes]:::solver
    SP[Split Detector<br/>by temp / weight / cube]:::solver
  end

  subgraph EXT["Azure platform services"]
    direction TB
    AM[Azure Maps<br/>Route Matrix · truck profile]:::ext
    AOAI[Azure OpenAI / Foundry<br/>GPT-4o · function calling]:::ext
    KV[Key Vault]:::ext
    AI[App Insights]:::ext
    COS[Cosmos DB<br/>session history]:::ext
  end

  subgraph MCP["MCP server (FastMCP)"]
    direction TB
    M1[parse · optimize · validate]:::mcp
    M2[reoptimize · explain · compare]:::mcp
    M3[delay_impact · sensitivity_lcv]:::mcp
  end

  subgraph DATA["Sample scenarios"]
    direction TB
    D1[standard_week]:::store
    D2[heavy_volume]:::store
    D3[tight_windows]:::store
    D4[long_haul_mix]:::store
  end

  U --> FE
  FE -->|HTTPS| BE
  UI1 -->|GET| API9
  UI2 -->|multipart| API1
  UI2 -->|multipart| API2
  UI3 -->|JSON| AOAI
  UI5 -->|POST| API7
  UI5 -->|POST| API8

  API1 --> P
  API2 --> P
  API2 --> S
  API3 --> V
  API4 --> S
  API5 --> V
  API6 --> S
  API7 --> S
  API8 --> S

  P --> D1
  P --> D2
  P --> D3
  P --> D4

  S -->|distance/time matrix| AM
  S --> V
  S --> SP

  AOAI -.tool calls.-> BE
  AOAI -.MCP.-> MCP
  MCP -.HTTP.-> BE
  BE --> KV
  BE --> AI
  BE --> COS
`;

const COMPONENTS = [
  {
    layer: 'Frontend',
    color: '#d52b1e',
    items: [
      ['React 18 + TypeScript + Vite', 'Single-page app, hot module reload, deployed as Static Web App'],
      ['Scenario picker', 'Dropdown: standard_week · heavy_volume · tight_windows · long_haul_mix — each preloaded with realistic exception triggers, plus a stale-result hint when the selection differs from the rendered run'],
      ['react-leaflet', 'Interactive route map with stop markers and per-route polylines'],
      ['Exception panel', '12 exception codes filterable by severity (violation / warning / info), color-coded badges'],
      ['Route summary table', 'Per-route status pills: window-at-risk, layover-required, off-interstate, low-utilization'],
      ['Delay impact panel', 'Click-through what-if: pick a route + delay (presets +30/+60/+90/+120/+180m), renders before/after arrival table inline with newly-late vs still-on-time counts'],
      ['Sensitivity panel', 'Click-through what-if: pick a trailer config grounded in the current solution + extra units (1–20), re-solves and shows side-by-side baseline vs scenario delta on cost, miles, route count'],
      ['mermaid', 'This dynamic architecture diagram, rendered client-side from text'],
    ],
  },
  {
    layer: 'Backend API',
    color: '#a86c00',
    items: [
      ['FastAPI 0.115 + Uvicorn', '9 REST endpoints: parse, optimize, validate, reoptimize, compare, explain, samples, delay-impact, sensitivity'],
      ['Pydantic v2 models', 'Strict typed contracts — orders, locations, trailer specs, routes, exceptions, splits'],
      ['Reoptimize knobs', 'capacity_relaxation_pct, window_slack_minutes, weather_overrides (per-state allow-list), priority_first'],
      ['Delay-impact endpoint', 'Cascades a manual delay through a route and lists every newly late stop'],
      ['Sensitivity endpoint', 'Adds N hypothetical LCV trailers, re-runs the solver, returns Δ cost/miles/routes'],
      ['Explain endpoint', 'Plain-English route narrative + equipment class + driver headroom + risk flags'],
      ['In-memory + optional Cosmos persistence', 'Sessions tied to one parse → optimize → reoptimize cycle'],
    ],
  },
  {
    layer: 'Optimization Core',
    color: '#2a8a2a',
    items: [
      ['Google OR-Tools (constraint_solver / RoutingModel)', 'Independent VRP per temperature group (AMBIENT, COOLER, FREEZER); PATH_CHEAPEST_ARC + GUIDED_LOCAL_SEARCH'],
      ['Distance matrix', 'Azure Maps Route Matrix v2 with truck profile; haversine fallback (×1.3, 55 mph) when offline'],
      ['Route Validator', '12 exception codes: cube/weight near + over capacity, delivery late, driver hours, window-at-risk, layover-required, LCB-off-interstate, long-inter-stop-hop, low-utilization, road-restriction-note'],
      ['Split detector', 'Flags any store served by 2+ routes, classifying reason as mixed_temp_zones / weight_over_one_trailer / cube_over_one_trailer'],
      ['Naive baseline calculator', 'One-truck-per-store reference cost — basis for the savings KPI'],
    ],
  },
  {
    layer: 'Sample scenarios',
    color: '#7a6f4a',
    items: [
      ['standard_week', '~70 orders. Balanced ordinary Monday dispatch — mostly clean, default demo scenario'],
      ['heavy_volume', '~110 orders ×2 cube/weight. Triggers cube/weight near-cap warnings + multi-route splits on hot stores'],
      ['tight_windows', '~100 orders, store windows compressed to 4 hours. Triggers WINDOW_AT_RISK + DELIVERY_LATE'],
      ['long_haul_mix', '~90 orders skewed to MT/WY + 10-hr HOS cap. Triggers LAYOVER_REQUIRED + LCB_OFF_INTERSTATE'],
    ],
  },
  {
    layer: 'MCP server',
    color: '#6c3fb5',
    items: [
      ['FastMCP streamable-HTTP', 'Listening on /mcp at the same Container App'],
      ['10 registered tools', 'parse, optimize, validate, reoptimize, compare, explain, delay_impact, sensitivity_lcv, get_samples, get_session'],
      ['Foundry-ready', 'Drop-in for any agent runtime that supports the MCP protocol (Foundry, Claude Desktop, Cursor, etc.)'],
    ],
  },
  {
    layer: 'Azure Platform',
    color: '#4a90e2',
    items: [
      ['Azure Maps Route Matrix v2', 'Truck-profile distance + time between every store pair (env: AZURE_MAPS_KEY)'],
      ['Azure Foundry / Azure OpenAI', 'GPT-4o function-calling drives the chat copilot using the 10 MCP tools'],
      ['Container Apps', 'Hosts the FastAPI backend + the MCP server with managed identity to Key Vault'],
      ['Static Web App (Free)', 'Hosts the Vite-built frontend bundle and proxies /api to the backend'],
      ['App Insights + Log Analytics', 'Traces every solve, parse error, agent tool call'],
      ['Key Vault', 'Stores Azure Maps key, Cosmos connection string, Foundry endpoint'],
      ['Cosmos DB (optional)', 'Write-only persistence for sessions, runs, and validation findings'],
    ],
  },
] as const;

const EXCEPTION_CODES = [
  ['CUBE_OVER_CAPACITY',     'VIOLATION', 'Total cube exceeds the trailer\'s degraded cube cap for that stop count'],
  ['WEIGHT_OVER_CAPACITY',   'VIOLATION', 'Total weight exceeds the trailer\'s rated weight cap'],
  ['DELIVERY_LATE',          'VIOLATION', 'Projected arrival is after the store\'s delivery window close'],
  ['DRIVER_HOURS_EXCEEDED',  'VIOLATION', 'Route exceeds the configured max_driver_hours (HOS cap)'],
  ['CUBE_NEAR_CAPACITY',     'WARNING',   'Cube utilization > 90% — risk of overflow if any order grows'],
  ['WEIGHT_NEAR_CAPACITY',   'WARNING',   'Weight utilization > 90%'],
  ['WINDOW_AT_RISK',         'WARNING',   'Projected arrival within 60 min of the store\'s closing time'],
  ['LAYOVER_REQUIRED',       'WARNING',   'Computed driver hours > 85% of HOS cap — overnight layover likely'],
  ['LCB_OFF_INTERSTATE',     'WARNING',   'Doubles route appears to leave the interstate in a state that requires interstate-only doubles'],
  ['LONG_INTER_STOP_HOP',    'INFO',      'Single inter-stop leg > 75 mi and > 1.75× the route\'s average leg'],
  ['LOW_UTILIZATION',        'INFO',      'Cube utilization < 55% — candidate for consolidation'],
  ['ROAD_RESTRICTION_NOTE',  'INFO',      'Route traverses a state with applicable trailer restrictions (informational only)'],
] as const;

export default function ArchitecturePage() {
  return (
    <div className="page">
      <header className="page-hero">
        <h1>How it works</h1>
        <p>
          A live view of every component that processes a dispatcher's input
          spreadsheets and produces an optimized fleet plan.
        </p>
      </header>

      <section className="diagram-card">
        <h2>System diagram</h2>
        <p className="diagram-sub">
          Solid arrows are HTTP calls; dotted arrows are agent tool invocations
          back into the backend.
        </p>
        <MermaidDiagram id="arch-diagram" chart={ARCH_DIAGRAM} />
        <div className="legend">
          <span><i style={{ background: '#fdf2f1', borderColor: '#d52b1e' }} />Frontend (React)</span>
          <span><i style={{ background: '#fef9e6', borderColor: '#a86c00' }} />Backend (FastAPI)</span>
          <span><i style={{ background: '#e6f4ea', borderColor: '#2a8a2a' }} />Solver core</span>
          <span><i style={{ background: '#eef5fc', borderColor: '#4a90e2' }} />Azure platform</span>
          <span><i style={{ background: '#f0e6ff', borderColor: '#6c3fb5' }} />MCP tools</span>
          <span><i style={{ background: '#f3eee2', borderColor: '#7a6f4a' }} />Sample scenarios</span>
        </div>
      </section>

      <section className="components">
        <h2>Component inventory</h2>
        {COMPONENTS.map((group) => (
          <div key={group.layer} className="component-group">
            <h3 style={{ borderColor: group.color, color: group.color }}>{group.layer}</h3>
            <div className="component-grid">
              {group.items.map(([name, desc]) => (
                <div key={name} className="component-card">
                  <div className="component-name">{name}</div>
                  <div className="component-desc">{desc}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </section>

      <section className="components">
        <h2>Exception codes the validator emits</h2>
        <p className="diagram-sub">
          The validator scans every solved route and emits a finding when a rule
          is broken or about to be broken. The dispatcher UI groups these by
          severity and lets you filter the panel.
        </p>
        <div className="exception-table">
          <div className="exception-row exception-head">
            <span>Code</span>
            <span>Severity</span>
            <span>What it means</span>
          </div>
          {EXCEPTION_CODES.map(([code, sev, desc]) => (
            <div key={code} className="exception-row">
              <span className="exc-code">{code}</span>
              <span className={`exc-sev exc-sev-${sev.toLowerCase()}`}>{sev}</span>
              <span>{desc}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="diagram-card">
        <h2>Request flow — running a sample scenario</h2>
        <MermaidDiagram
          id="seq-diagram"
          chart={`
sequenceDiagram
  autonumber
  participant U as Dispatcher
  participant FE as React UI
  participant BE as FastAPI
  participant P as Parsers
  participant S as OR-Tools
  participant V as Validator
  participant AM as Azure Maps
  U->>FE: Pick scenario, click Run
  FE->>BE: POST /api/optimize-from-samples?scenario=heavy_volume
  BE->>P: Read scenario folder (orders/locations/constraints)
  P-->>BE: Pydantic-validated bundle
  BE->>AM: Route Matrix (truck profile)
  AM-->>BE: Distance + time per OD pair
  BE->>S: Solve VRP per temperature group
  S-->>BE: Routes + splits
  BE->>V: Validate routes vs all rules
  V-->>BE: Exceptions (12 codes, 3 severities)
  BE-->>FE: OptimizationResult JSON (routes, KPIs, splits, exceptions)
  FE-->>U: Map · KPIs · table · filtered exception panel · what-if panels
  U->>FE: Open Delay Impact panel, pick route + 90 min
  FE->>BE: POST /api/delay-impact (route_id, 90)
  BE-->>FE: Original → projected arrivals + newly-late stops
  U->>FE: Open Sensitivity panel, +2 SINGLE_53
  FE->>BE: POST /api/sensitivity/lcv-availability
  BE->>S: Re-solve with capacity headroom
  S-->>BE: Scenario routes
  BE-->>FE: Baseline vs scenario delta + summary
`}
        />
      </section>
    </div>
  );
}
