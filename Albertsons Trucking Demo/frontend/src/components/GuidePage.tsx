import { SAMPLE_FILES, sampleUrl } from '../services/apiClient';

export default function GuidePage() {
  return (
    <div className="page">
      <header className="page-hero">
        <h1>User guide</h1>
        <p>
          Everything a dispatcher or planning analyst needs to plan tomorrow's
          truckloads with this tool — purpose, inputs, workflow, and what the
          numbers mean.
        </p>
      </header>

      {/* Purpose ─────────────────────────────────────────────────────── */}
      <section className="guide-card">
        <h2>What this tool is for</h2>
        <p>
          The Albertsons Routing Copilot turns a day's worth of store orders into
          a cost-optimized truck plan out of the Salt Lake City Distribution
          Center. It serves stores across <strong>UT, ID, WY, MT, and CO</strong>{' '}
          (Albertsons + Safeway banners) and respects the same real-world
          constraints a human dispatcher would weigh:
        </p>
        <ul className="bullet-list">
          <li><strong>Cold-chain separation</strong> — ambient, cooler, and freezer loads never share a trailer compartment.</li>
          <li><strong>Trailer mix</strong> — combos (40-40, 45-45, 48-28) and single 53-footers, each with its own weight, cube, and stop limits.</li>
          <li><strong>State-aware weight rules</strong> — Wyoming's tighter 80,000 lb gross ceiling for combo trailers.</li>
          <li><strong>Cube degradation</strong> — usable cube drops as stops increase (loaders re-pack at every stop).</li>
          <li><strong>Driver hours of service</strong> — 11-hour driving cap, 30-minute service per stop.</li>
          <li><strong>Delivery windows</strong> — each store's receiving hours.</li>
        </ul>
        <p className="callout">
          The output is a set of route assignments, a fleet cost figure, and a
          ranked list of exceptions for any rule the optimizer had to bend.
          A human still owns the final dispatch decision.
        </p>
      </section>

      {/* Inputs ──────────────────────────────────────────────────────── */}
      <section className="guide-card">
        <h2>Input documents</h2>
        <p>
          The tool reads three files. Click any tile below to download the
          working sample for that file and use it as a template.
        </p>
        <div className="sample-strip">
          {SAMPLE_FILES.map((s) => (
            <a key={s.key} className="sample-card" href={sampleUrl(s.key)} download={s.filename}>
              <span className="sample-icon">{s.icon}</span>
              <span className="sample-text">
                <span className="sample-title">{s.label}</span>
                <span className="sample-sub">{s.sublabel}</span>
              </span>
              <span className="sample-dl">↓</span>
            </a>
          ))}
        </div>

        <h3>1 · Orders file (CSV or XLSX)</h3>
        <p>One row per order. Required columns:</p>
        <table className="schema-table">
          <thead><tr><th>Column</th><th>Type</th><th>Description</th></tr></thead>
          <tbody>
            <tr><td><code>order_id</code></td><td>string</td><td>Unique key. Anything stable; we surface it in route detail.</td></tr>
            <tr><td><code>store_code</code></td><td>string</td><td>Must match a <code>location_code</code> in the locations file.</td></tr>
            <tr><td><code>commodity_group</code></td><td>enum</td><td><code>AMBIENT</code> | <code>COOLER_34_38F</code> | <code>FREEZER_0F</code></td></tr>
            <tr><td><code>weight_lbs</code></td><td>number</td><td>Order weight in pounds.</td></tr>
            <tr><td><code>cube</code></td><td>number</td><td>Volume in cubic feet.</td></tr>
            <tr><td><code>cases</code></td><td>integer</td><td>Case count (informational; helps the validator with packing realism).</td></tr>
            <tr><td><code>delivery_date</code></td><td>YYYY-MM-DD</td><td>Date the load must arrive.</td></tr>
          </tbody>
        </table>

        <h3>2 · Locations file (XLSX)</h3>
        <p>One row per stop, including the originating DC.</p>
        <table className="schema-table">
          <thead><tr><th>Column</th><th>Type</th><th>Description</th></tr></thead>
          <tbody>
            <tr><td><code>location_code</code></td><td>string</td><td>Used by orders to reference this stop.</td></tr>
            <tr><td><code>location_name</code></td><td>string</td><td>Friendly name shown on the map and in the route table.</td></tr>
            <tr><td><code>location_type</code></td><td>enum</td><td><code>DC</code> for the depot, <code>STORE</code> for everything else.</td></tr>
            <tr><td><code>latitude</code> / <code>longitude</code></td><td>number</td><td>Decimal degrees (WGS84).</td></tr>
            <tr><td><code>state</code></td><td>2-char</td><td>USPS state code — used for road/weight rules.</td></tr>
            <tr><td><code>delivery_window_open</code> / <code>_close</code></td><td>HH:MM</td><td>Receiving hours.</td></tr>
          </tbody>
        </table>

        <h3>3 · Constraints workbook (XLSX, multi-sheet)</h3>
        <table className="schema-table">
          <thead><tr><th>Sheet</th><th>Rows</th><th>Purpose</th></tr></thead>
          <tbody>
            <tr><td><code>trailer_types</code></td><td>4</td><td>Each config's max weight, max single-stop cube, and max stops.</td></tr>
            <tr><td><code>cube_degradation</code></td><td>~30</td><td>Cube cap by stop count per trailer config (loaders re-stack at every stop).</td></tr>
            <tr><td><code>road_restrictions</code></td><td>~10</td><td>State-level overrides (e.g., WY 80,000 lb cap for combos).</td></tr>
            <tr><td><code>costs</code></td><td>2</td><td><code>per_mile</code> and <code>per_stop</code> dollar values for the objective function.</td></tr>
          </tbody>
        </table>
      </section>

      {/* Workflow ────────────────────────────────────────────────────── */}
      <section className="guide-card">
        <h2>Workflow — three modes</h2>

        <h3>Mode A · Try the sample</h3>
        <ol className="numbered-list">
          <li>Open the <em>Optimizer</em> tab.</li>
          <li>Click <strong>▶ Try it with sample data</strong>.</li>
          <li>Review the KPI cards, route map, and exception panel.</li>
        </ol>

        <h3>Mode B · Bring your own data</h3>
        <ol className="numbered-list">
          <li>Download the three sample files to use as a template.</li>
          <li>Replace rows with your real orders, stores, and constraints. Keep the column headers exactly.</li>
          <li>Upload the three files in the <em>Upload your files</em> panel.</li>
          <li>Click <strong>Parse + Optimize</strong>. The solver typically finishes in 15–30 s.</li>
        </ol>

        <h3>Mode C · Conversational re-planning</h3>
        <p>
          After an initial optimization, use the chat panel to explore
          alternatives without re-uploading anything. Examples it understands:
        </p>
        <ul className="bullet-list">
          <li>"What if we lose all 45-45 trailers tomorrow?"</li>
          <li>"Drop store ALB-MT-MISA from this run — they had a fire."</li>
          <li>"Explain route R03"</li>
          <li>"Validate the current plan"</li>
          <li>"Run the optimizer with the sample data"</li>
        </ul>
      </section>

      {/* Reading results ────────────────────────────────────────────── */}
      <section className="guide-card">
        <h2>Reading the results</h2>

        <h3>KPI cards</h3>
        <table className="schema-table">
          <thead><tr><th>Card</th><th>What it means</th></tr></thead>
          <tbody>
            <tr><td><strong>Routes</strong></td><td>Number of trucks dispatched, with on-time / flagged split.</td></tr>
            <tr><td><strong>Total miles</strong></td><td>Sum across all dispatched trucks for the day.</td></tr>
            <tr><td><strong>Total cost</strong></td><td><code>per_mile × miles + per_stop × stops</code> using your constraints workbook.</td></tr>
            <tr><td><strong>Savings</strong></td><td>vs. a naive baseline of one dedicated truck per (store, temp). Higher is better.</td></tr>
            <tr><td><strong>Cube fill</strong></td><td>Average % of usable cube actually used. Aim for 80%+.</td></tr>
            <tr><td><strong>Exceptions</strong></td><td>Count of issues the validator flagged for human review.</td></tr>
          </tbody>
        </table>

        <h3>Exceptions — severity legend</h3>
        <ul className="severity-list">
          <li><span className="sev-dot violation" /> <strong>Violation</strong> — a hard rule was broken (cube/weight overcap, late delivery, HOS). Must be resolved before dispatch.</li>
          <li><span className="sev-dot warning" /> <strong>Warning</strong> — soft preference broken (e.g. road note). Review but usually OK.</li>
          <li><span className="sev-dot info" /> <strong>Info</strong> — informational notes the planner should know.</li>
        </ul>
      </section>

      {/* FAQ ────────────────────────────────────────────────────────── */}
      <section className="guide-card">
        <h2>FAQ</h2>

        <details>
          <summary>Why are some routes longer than 11 hours?</summary>
          <p>
            The solver allows multi-day routes by design (a Kalispell, MT haul
            is naturally a 2-day run). The validator then flags{' '}
            <code>DRIVER_HOURS_EXCEEDED</code> so you can plan a relay, team
            driver, or over-the-road resource.
          </p>
        </details>

        <details>
          <summary>Why does my run show a haversine fallback notice?</summary>
          <p>
            Azure Maps wasn't reachable (no <code>AZURE_MAPS_KEY</code> set, or
            the call failed). The solver fell back to great-circle distance ×
            1.3 inflation at 55 mph. Set the env var to enable real
            truck-routed mileage.
          </p>
        </details>

        <details>
          <summary>Can I add my own constraints?</summary>
          <p>
            Yes — the <code>constraints.xlsx</code> workbook is the single
            source of truth for trailer mix, weight ceilings, cube degradation,
            and pricing. Add rows to <code>road_restrictions</code> for new
            state rules; the validator picks them up automatically.
          </p>
        </details>

        <details>
          <summary>Is the data persisted anywhere?</summary>
          <p>
            Not in this proof of concept. Sessions live in the backend's
            in-memory store and disappear when the service restarts. A
            production deployment would back this with Azure Cosmos DB or
            Postgres.
          </p>
        </details>

        <details>
          <summary>How accurate are the cost numbers?</summary>
          <p>
            The cost model is intentionally simple — per-mile + per-stop —
            because that's the contract dispatchers reason about. You can edit
            both rates in the <code>costs</code> sheet of the constraints
            workbook to match your carrier agreements.
          </p>
        </details>
      </section>
    </div>
  );
}
