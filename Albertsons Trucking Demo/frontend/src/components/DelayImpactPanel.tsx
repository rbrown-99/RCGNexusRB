import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { delayImpact } from '../services/apiClient';

interface Props {
  sessionId?: string;
  routes: Route[];
}

interface ProjectedStop {
  location_code: string;
  location_name: string;
  arrival_clock: string;
  arrival_min: number;
  window_close_min: number;
  late_by_min: number;
  on_time: boolean;
}

interface OriginalStop {
  location_code: string;
  location_name: string;
  arrival_clock: string;
  arrival_min: number;
  window_open_min: number;
  window_close_min: number;
  on_time: boolean;
}

interface DelayResponse {
  session_id: string;
  route_id: string;
  delay_minutes: number;
  original_arrivals: OriginalStop[];
  projected_arrivals: ProjectedStop[];
  newly_late_stops: string[];
  still_on_time_count: number;
  summary: string;
}

const PRESETS = [30, 60, 90, 120, 180];

function hhmm(minutes: number) {
  const m = ((Math.round(minutes) % (24 * 60)) + 24 * 60) % (24 * 60);
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
}

/**
 * Click-through panel for /api/delay-impact — pick a route, choose a delay,
 * see which stops will miss their window and by how much.
 */
export default function DelayImpactPanel({ sessionId, routes }: Props) {
  const sortedRoutes = useMemo(
    () => [...routes].sort((a, b) => a.route_id.localeCompare(b.route_id)),
    [routes],
  );
  const [selectedRoute, setSelectedRoute] = useState<string>(
    sortedRoutes[0]?.route_id ?? '',
  );
  const [delayMin, setDelayMin] = useState<number>(60);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [result, setResult] = useState<DelayResponse | null>(null);

  // If the route list changes (new optimization), reset and pick the first.
  useEffect(() => {
    if (sortedRoutes.length === 0) {
      setSelectedRoute('');
      setResult(null);
      return;
    }
    if (!sortedRoutes.find((r) => r.route_id === selectedRoute)) {
      setSelectedRoute(sortedRoutes[0].route_id);
      setResult(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedRoutes]);

  async function run() {
    if (!sessionId || !selectedRoute) return;
    setBusy(true);
    setErr(null);
    try {
      const r = (await delayImpact(sessionId, selectedRoute, delayMin)) as DelayResponse;
      setResult(r);
    } catch (e: any) {
      setErr(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  }

  const newlyLate = result?.newly_late_stops?.length ?? 0;
  const stillOnTime = result?.still_on_time_count ?? 0;

  return (
    <div className="analysis-panel delay-panel">
      <div className="analysis-header">
        <h4>Delay impact</h4>
        <span className="analysis-tag">What-if</span>
      </div>
      <p className="analysis-help">
        Hold a route by N minutes and see which stops slip outside their delivery window.
      </p>

      <div className="analysis-controls">
        <label className="analysis-field">
          <span>Route</span>
          <select
            value={selectedRoute}
            onChange={(e) => {
              setSelectedRoute(e.target.value);
              setResult(null);
            }}
            disabled={busy || sortedRoutes.length === 0}
          >
            {sortedRoutes.length === 0 ? (
              <option value="">(no routes — run optimize first)</option>
            ) : (
              sortedRoutes.map((r) => (
                <option key={r.route_id} value={r.route_id}>
                  {r.route_id} · {r.trailer_config} · {r.stops.length} stops
                </option>
              ))
            )}
          </select>
        </label>

        <label className="analysis-field analysis-field-narrow">
          <span>Delay (min)</span>
          <input
            type="number"
            min={0}
            max={720}
            step={15}
            value={delayMin}
            onChange={(e) => setDelayMin(Math.max(0, Number(e.target.value) || 0))}
            disabled={busy}
          />
        </label>

        <div className="analysis-presets">
          {PRESETS.map((p) => (
            <button
              key={p}
              type="button"
              className={`preset-chip ${delayMin === p ? 'active' : ''}`}
              onClick={() => setDelayMin(p)}
              disabled={busy}
            >
              +{p}m
            </button>
          ))}
        </div>

        <button
          type="button"
          className="analysis-cta"
          onClick={run}
          disabled={busy || !sessionId || !selectedRoute}
        >
          {busy ? <><span className="spinner" /> Projecting…</> : 'Project delay'}
        </button>
      </div>

      {err && <div className="analysis-err">Error: {err}</div>}

      {result && !err && (
        <>
          <div className="analysis-summary">
            <div className="summary-stat summary-stat-bad">
              <div className="stat-value">{newlyLate}</div>
              <div className="stat-label">Newly late stops</div>
            </div>
            <div className="summary-stat summary-stat-good">
              <div className="stat-value">{stillOnTime}</div>
              <div className="stat-label">Still on time</div>
            </div>
            <div className="summary-text">{result.summary}</div>
          </div>

          <div className="analysis-table-wrap">
            <table className="analysis-table">
              <thead>
                <tr>
                  <th>Stop</th>
                  <th>Original</th>
                  <th>Projected</th>
                  <th>Window close</th>
                  <th>Late by</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {result.projected_arrivals.map((p, i) => {
                  const orig = result.original_arrivals[i];
                  const wasLate = orig ? !orig.on_time : false;
                  const becameLate = !p.on_time && !wasLate;
                  return (
                    <tr key={p.location_code} className={p.on_time ? '' : 'row-late'}>
                      <td>
                        <div className="stop-code">{p.location_code}</div>
                        <div className="stop-name">{p.location_name}</div>
                      </td>
                      <td className="mono">{orig?.arrival_clock ?? '—'}</td>
                      <td className="mono">{p.arrival_clock}</td>
                      <td className="mono">{hhmm(p.window_close_min)}</td>
                      <td className={p.late_by_min > 0 ? 'late-amount' : 'mono-muted'}>
                        {p.late_by_min > 0 ? `+${p.late_by_min}m` : '—'}
                      </td>
                      <td>
                        {p.on_time ? (
                          <span className="status-pill status-ok">On time</span>
                        ) : becameLate ? (
                          <span className="status-pill status-violation">Newly late</span>
                        ) : (
                          <span className="status-pill status-late">Was late</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}

      {!result && !err && (
        <div className="analysis-empty">
          Pick a route, choose a delay, and click <strong>Project delay</strong> to see
          downstream impact. No re-solve needed.
        </div>
      )}
    </div>
  );
}
