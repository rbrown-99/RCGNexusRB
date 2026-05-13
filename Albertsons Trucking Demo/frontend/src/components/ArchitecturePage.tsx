import MermaidDiagram from './MermaidDiagram';

const ARCH_DIAGRAM = `
flowchart LR
  classDef user fill:#fff,stroke:#1f2330,stroke-width:2px,color:#1f2330
  classDef ui fill:#fdf2f1,stroke:#d52b1e,stroke-width:2px,color:#1f2330
  classDef api fill:#fef9e6,stroke:#a86c00,stroke-width:2px,color:#1f2330
  classDef solver fill:#e6f4ea,stroke:#2a8a2a,stroke-width:2px,color:#1f2330
  classDef ext fill:#eef5fc,stroke:#4a90e2,stroke-width:2px,color:#1f2330
  classDef store fill:#f3eee2,stroke:#7a6f4a,stroke-width:2px,color:#1f2330

  U([Dispatcher / Business User]):::user

  subgraph FE["Frontend — React + TypeScript + Vite"]
    direction TB
    UI1[Sample Downloads]:::ui
    UI2[File Upload]:::ui
    UI3[Chat Copilot]:::ui
    UI4[Route Map · KPI Cards · Tables]:::ui
  end

  subgraph BE["Backend — FastAPI on Container Apps"]
    direction TB
    API1["/api/parse"]:::api
    API2["/api/optimize"]:::api
    API3["/api/validate"]:::api
    API4["/api/reoptimize"]:::api
    API5["/api/explain"]:::api
    API6["/api/samples"]:::api
  end

  subgraph CORE["Core engines"]
    direction TB
    P[Pandas / openpyxl<br/>parsers]:::solver
    S[OR-Tools CP-SAT<br/>multi-temp VRP]:::solver
    V[Route Validator<br/>cube · weight · HOS · windows]:::solver
  end

  subgraph EXT["Azure platform services"]
    direction TB
    AM[Azure Maps<br/>Route Matrix · truck profile]:::ext
    AOAI[Azure OpenAI / Foundry<br/>GPT-4o · function calling]:::ext
    KV[Key Vault]:::ext
    AI[App Insights]:::ext
  end

  subgraph DATA["Inputs"]
    direction TB
    O[orders.csv]:::store
    L[locations.xlsx]:::store
    C[constraints.xlsx]:::store
  end

  U --> FE
  FE -->|HTTPS| BE
  UI1 -->|GET| API6
  UI2 -->|multipart| API1
  UI2 -->|multipart| API2
  UI3 -->|JSON| AOAI

  API1 --> P
  API2 --> P
  API2 --> S
  API3 --> V
  API4 --> S
  API5 --> V

  P --> O
  P --> L
  P --> C
  S -->|distance/time matrix| AM
  S --> V

  AOAI -.tool calls.-> BE
  BE --> KV
  BE --> AI
`;

const COMPONENTS = [
  {
    layer: 'Frontend',
    color: '#d52b1e',
    items: [
      ['React 18 + TypeScript + Vite', 'Single-page app, hot module reload, deployed as Static Web App'],
      ['react-leaflet', 'Interactive route map with stop markers and per-route polylines'],
      ['mermaid', 'This dynamic architecture diagram, rendered client-side from text'],
      ['Native fetch + EventSource', 'Streams optimization runs and chat responses from the backend'],
    ],
  },
  {
    layer: 'Backend API',
    color: '#a86c00',
    items: [
      ['FastAPI 0.115 + Uvicorn', '6 REST endpoints: parse, optimize, validate, reoptimize, compare, explain (+ samples)'],
      ['Pydantic v2 models', 'Strict typed contracts for orders, locations, trailer specs, routes, exceptions'],
      ['In-memory session store', 'Stateful sessions tied to one parse → optimize → reoptimize cycle (POC)'],
      ['Multipart upload', 'Accepts CSV / XLSX up to 10 MB per file'],
    ],
  },
  {
    layer: 'Optimization Core',
    color: '#2a8a2a',
    items: [
      ['Google OR-Tools (CP-SAT routing)', 'Vehicle Routing Problem solver, one model per temperature group'],
      ['Pandas + openpyxl', 'Reads orders / locations / constraints workbooks, normalizes column names'],
      ['Route Validator', 'Post-solve checks: cube degradation, state-aware weight caps, driver hours, delivery windows'],
      ['Naive baseline calculator', 'One-truck-per-store reference cost — basis for the savings KPI'],
    ],
  },
  {
    layer: 'Azure Platform',
    color: '#4a90e2',
    items: [
      ['Azure Maps Route Matrix v2', 'Truck-profile distance + time between every store pair (env: AZURE_MAPS_KEY)'],
      ['Azure Foundry / Azure OpenAI', 'GPT-4o function-calling drives the chat copilot using our 6 tools as actions'],
      ['Container Apps', 'Hosts the FastAPI backend with managed identity to Key Vault'],
      ['Static Web App (Free)', 'Hosts the Vite-built frontend bundle and proxies /api to the backend'],
      ['App Insights + Log Analytics', 'Traces every solve, parse error, agent tool call'],
      ['Key Vault', 'Stores Azure Maps key and any Foundry connection strings'],
    ],
  },
  {
    layer: 'Inputs',
    color: '#7a6f4a',
    items: [
      ['orders.csv', 'order_id, store_code, commodity_group, weight_lbs, cube, cases, delivery_date'],
      ['locations.xlsx', 'location_code, name, type (DC|STORE), lat, lon, state, delivery_window_open/close'],
      ['constraints.xlsx', 'Sheets: trailer_types, cube_degradation, road_restrictions, costs'],
    ],
  },
] as const;

export default function ArchitecturePage() {
  return (
    <div className="page">
      <header className="page-hero">
        <h1>How it works</h1>
        <p>
          A live view of every component that processes a dispatcher's input
          spreadsheets and produces an optimized fleet plan. Drag, scroll, or
          zoom the diagram below.
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
          <span><i style={{ background: '#f3eee2', borderColor: '#7a6f4a' }} />Input files</span>
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

      <section className="diagram-card">
        <h2>Request flow — running the sample dataset</h2>
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
  U->>FE: Click "Try with sample data"
  FE->>BE: POST /api/optimize-from-samples
  BE->>P: Read orders / locations / constraints
  P-->>BE: Pydantic-validated bundle
  BE->>AM: Route Matrix (truck profile)
  AM-->>BE: Distance + time per OD pair
  BE->>S: Solve VRP per temperature group
  S-->>BE: Routes (stops · miles · cost)
  BE->>V: Validate routes vs all rules
  V-->>BE: Exceptions (cube · HOS · windows)
  BE-->>FE: OptimizationResult JSON
  FE-->>U: Map · KPIs · table · exceptions
`}
        />
      </section>
    </div>
  );
}
