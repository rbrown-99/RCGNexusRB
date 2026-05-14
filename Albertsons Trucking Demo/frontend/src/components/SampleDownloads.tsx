import { useEffect, useState } from 'react';
import { SAMPLE_FILES, sampleUrl, getSampleCatalog, type ScenarioCatalogItem } from '../services/apiClient';

interface Props {
  onRunSample: (scenario: string) => void;
  busy: boolean;
  /** Scenario key whose results are currently rendered on the right pane (if any). */
  lastRunScenario?: string;
}

const FALLBACK_SCENARIOS: ScenarioCatalogItem[] = [
  { key: 'standard_week', label: 'Standard Week',
    blurb: 'Balanced ordinary Monday dispatch — most routes on time.',
    highlights: ['Default baseline', 'Few exceptions', 'Healthy savings vs naive'] },
  { key: 'heavy_volume', label: 'Heavy Volume',
    blurb: 'Roughly 2× per-order weight + cube. Triggers cube/weight near-cap warnings and forces splits.',
    highlights: ['CUBE_NEAR_CAPACITY', 'WEIGHT_NEAR_CAPACITY', 'Splits on hot stores'] },
  { key: 'tight_windows', label: 'Tight Windows',
    blurb: "Every store's delivery window compressed to 4 hours. Triggers WINDOW_AT_RISK and DELIVERY_LATE.",
    highlights: ['WINDOW_AT_RISK', 'DELIVERY_LATE', 'Sequencing pressure'] },
  { key: 'long_haul_mix', label: 'Long-haul Mix',
    blurb: 'Demand skewed to MT/WY long-haul stores + tighter 10-hour HOS. Triggers LAYOVER and LCB_OFF_INTERSTATE.',
    highlights: ['LAYOVER_REQUIRED', 'LCB_OFF_INTERSTATE', 'Long inter-stop hops'] },
];

const SCENARIO_ICONS: Record<string, string> = {
  standard_week: '📅',
  heavy_volume:  '📦',
  tight_windows: '⏱',
  long_haul_mix: '🛣',
};

/**
 * Business-user-friendly panel that:
 *  1. Lets the dispatcher pick a scenario (Standard Week, Heavy Volume, …).
 *  2. Downloads the three example files for that scenario.
 *  3. One-click "Try it with sample data" to run the optimizer end-to-end.
 */
export default function SampleDownloads({ onRunSample, busy, lastRunScenario }: Props) {
  const [scenarios, setScenarios] = useState<ScenarioCatalogItem[]>(FALLBACK_SCENARIOS);
  const [selected, setSelected] = useState<string>('standard_week');

  useEffect(() => {
    getSampleCatalog()
      .then((cat) => {
        if (cat.scenarios && cat.scenarios.length > 0) setScenarios(cat.scenarios);
      })
      .catch(() => {/* keep fallback */});
  }, []);

  const current = scenarios.find((s) => s.key === selected) ?? scenarios[0];
  const lastRunLabel = lastRunScenario
    ? scenarios.find((s) => s.key === lastRunScenario)?.label ?? lastRunScenario
    : undefined;
  const showStaleHint =
    lastRunScenario !== undefined && lastRunScenario !== selected && !busy;

  return (
    <div className="samples">
      <h3>Sample dataset</h3>

      <div className="scenario-picker">
        <label className="scenario-picker-label" htmlFor="scenario-select">
          Scenario
        </label>
        <div className="scenario-select-wrap">
          <select
            id="scenario-select"
            className="scenario-select"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            disabled={busy}
          >
            {scenarios.map((s) => (
              <option key={s.key} value={s.key}>
                {(SCENARIO_ICONS[s.key] || '•') + '  ' + s.label}
              </option>
            ))}
          </select>
        </div>
        {current && (
          <div className="scenario-card">
            <div className="scenario-blurb">{current.blurb}</div>
            <div className="scenario-highlights">
              {current.highlights.map((h) => (
                <span key={h} className="scenario-pill">{h}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="samples-list">
        {SAMPLE_FILES.map(s => (
          <a
            key={s.key}
            className="sample-card"
            href={sampleUrl(s.key, selected)}
            download={`${selected}_${s.filename}`}
            title={`Download ${s.filename} for ${current?.label ?? selected}`}
          >
            <span className="sample-icon" aria-hidden>{s.icon}</span>
            <span className="sample-text">
              <span className="sample-title">{s.label}</span>
              <span className="sample-sub">{s.sublabel}</span>
            </span>
            <span className="sample-dl" aria-hidden>↓</span>
          </a>
        ))}
      </div>

      <button className="primary-cta" disabled={busy} onClick={() => onRunSample(selected)}>
        {busy ? (
          <><span className="spinner" /> Optimizing routes…</>
        ) : (
          <>▶ Try it with the {current?.label ?? 'selected'} scenario</>
        )}
      </button>
      {showStaleHint && (
        <div className="scenario-stale-hint" role="status">
          <span className="stale-dot" aria-hidden />
          Showing <strong>{lastRunLabel}</strong> results. Click above to refresh
          with <strong>{current?.label ?? selected}</strong>.
        </div>
      )}
      <p className="samples-foot">No data setup required — runs end-to-end in seconds.</p>
    </div>
  );
}
