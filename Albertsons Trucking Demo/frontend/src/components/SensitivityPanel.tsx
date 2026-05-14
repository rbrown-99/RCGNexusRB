import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { sensitivityLcv } from '../services/apiClient';

interface Props {
  sessionId?: string;
  routes: Route[];
}

interface SensitivitySummary {
  total_routes: number;
  total_cost_usd: number;
  total_miles: number;
  lcv_routes_used: number;
  average_weight_utilization: number;
  average_cube_utilization: number;
}

interface SensitivityResponse {
  session_id: string;
  extra_lcv_units: number;
  lcv_trailer_config: string;
  baseline: SensitivitySummary;
  scenario: SensitivitySummary;
  delta: {
    routes: number;
    cost_usd: number;
    miles: number;
    lcv_routes_used: number;
  };
  summary: string;
}

const KNOWN_LCV_CONFIGS = ['SINGLE_53', '48-28_COMBO', '45-45_COMBO', '53-28_COMBO'];

function fmtMoney(n: number) {
  const sign = n < 0 ? '-' : n > 0 ? '+' : '';
  return `${sign}$${Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function fmtPlain(n: number) {
  return `$${n.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function pct(n: number) {
  return `${(n * 100).toFixed(0)}%`;
}

/**
 * Click-through panel for /api/sensitivity/lcv-availability — pick a trailer
 * config and see whether adding more units of it would lower cost / route count.
 */
export default function SensitivityPanel({ sessionId, routes }: Props) {
  // Detect trailer configs actually present in the current solution, so the
  // dropdown is grounded in this session.
  const availableConfigs = useMemo(() => {
    const present = new Set(routes.map((r) => r.trailer_config));
    const ordered: string[] = [];
    for (const c of KNOWN_LCV_CONFIGS) if (present.has(c)) ordered.push(c);
    for (const c of present) if (!ordered.includes(c)) ordered.push(c);
    return ordered;
  }, [routes]);

  const [config, setConfig] = useState<string>(availableConfigs[0] ?? 'SINGLE_53');
  const [extraUnits, setExtraUnits] = useState<number>(2);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<SensitivityResponse | null>(null);

  useEffect(() => {
    if (availableConfigs.length === 0) return;
    if (!availableConfigs.includes(config)) {
      setConfig(availableConfigs[0]);
      setResult(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [availableConfigs.join('|')]);

  async function run() {
    if (!sessionId) return;
    setBusy(true);
    setErr(null);
    try {
      const r = (await sensitivityLcv(sessionId, extraUnits, config)) as SensitivityResponse;
      setResult(r);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const delta = result?.delta;
  const isImprovement = delta && (delta.cost_usd < 0 || delta.routes < 0);
  const isNoChange = delta && delta.routes === 0 && Math.abs(delta.cost_usd) < 1;

  return (
    <div className="analysis-panel sensitivity-panel">
      <div className="analysis-header">
        <h4>Capacity sensitivity</h4>
        <span className="analysis-tag">What-if</span>
      </div>
      <p className="analysis-help">
        Estimate the impact of adding more units of a trailer configuration.
        Re-runs the optimizer with extra capacity headroom.
      </p>

      <div className="analysis-controls">
        <label className="analysis-field">
          <span>Trailer config</span>
          <select
            value={config}
            onChange={(e) => {
              setConfig(e.target.value);
              setResult(null);
            }}
            disabled={busy || availableConfigs.length === 0}
          >
            {availableConfigs.length === 0 ? (
              <option value="">(no routes — run optimize first)</option>
            ) : (
              availableConfigs.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))
            )}
          </select>
        </label>

        <label className="analysis-field analysis-field-narrow">
          <span>Extra units</span>
          <input
            type="number"
            min={1}
            max={20}
            step={1}
            value={extraUnits}
            onChange={(e) => setExtraUnits(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
            disabled={busy}
          />
        </label>

        <button
          type="button"
          className="analysis-cta"
          onClick={run}
          disabled={busy || !sessionId || availableConfigs.length === 0}
        >
          {busy ? <><span className="spinner" /> Re-solving…</> : 'Run sensitivity'}
        </button>
      </div>

      {err && <div className="analysis-err">Error: {err}</div>}

      {result && !err && (
        <>
          <div className={`sensitivity-callout ${isImprovement ? 'good' : isNoChange ? 'neutral' : 'mixed'}`}>
            {result.summary}
          </div>

          <div className="analysis-table-wrap">
            <table className="analysis-table sensitivity-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  <th>Baseline</th>
                  <th>+{result.extra_lcv_units} {result.lcv_trailer_config}</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Routes</td>
                  <td className="mono">{result.baseline.total_routes}</td>
                  <td className="mono">{result.scenario.total_routes}</td>
                  <td className={`mono ${result.delta.routes < 0 ? 'delta-good' : result.delta.routes > 0 ? 'delta-bad' : ''}`}>
                    {result.delta.routes > 0 ? `+${result.delta.routes}` : result.delta.routes}
                  </td>
                </tr>
                <tr>
                  <td>Total cost</td>
                  <td className="mono">{fmtPlain(result.baseline.total_cost_usd)}</td>
                  <td className="mono">{fmtPlain(result.scenario.total_cost_usd)}</td>
                  <td className={`mono ${result.delta.cost_usd < 0 ? 'delta-good' : result.delta.cost_usd > 0 ? 'delta-bad' : ''}`}>
                    {fmtMoney(result.delta.cost_usd)}
                  </td>
                </tr>
                <tr>
                  <td>Total miles</td>
                  <td className="mono">{result.baseline.total_miles.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                  <td className="mono">{result.scenario.total_miles.toLocaleString('en-US', { maximumFractionDigits: 0 })}</td>
                  <td className={`mono ${result.delta.miles < 0 ? 'delta-good' : result.delta.miles > 0 ? 'delta-bad' : ''}`}>
                    {result.delta.miles > 0 ? '+' : ''}{result.delta.miles.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </td>
                </tr>
                <tr>
                  <td>{result.lcv_trailer_config} routes</td>
                  <td className="mono">{result.baseline.lcv_routes_used}</td>
                  <td className="mono">{result.scenario.lcv_routes_used}</td>
                  <td className={`mono ${result.delta.lcv_routes_used > 0 ? 'delta-good' : result.delta.lcv_routes_used < 0 ? 'delta-bad' : ''}`}>
                    {result.delta.lcv_routes_used > 0 ? `+${result.delta.lcv_routes_used}` : result.delta.lcv_routes_used}
                  </td>
                </tr>
                <tr>
                  <td>Avg weight util</td>
                  <td className="mono">{pct(result.baseline.average_weight_utilization)}</td>
                  <td className="mono">{pct(result.scenario.average_weight_utilization)}</td>
                  <td className="mono mono-muted">—</td>
                </tr>
                <tr>
                  <td>Avg cube util</td>
                  <td className="mono">{pct(result.baseline.average_cube_utilization)}</td>
                  <td className="mono">{pct(result.scenario.average_cube_utilization)}</td>
                  <td className="mono mono-muted">—</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      {!result && !err && (
        <div className="analysis-empty">
          Pick a trailer config and click <strong>Run sensitivity</strong> to see whether
          adding more units would reduce cost or route count for this scenario.
        </div>
      )}
    </div>
  );
}
