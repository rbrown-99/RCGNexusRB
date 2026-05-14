import type { OptimizeResponse } from '../types';

export const BASE = (import.meta.env.VITE_BACKEND_URL as string) || 'http://localhost:8000';

export const SAMPLE_FILES = [
  { key: 'orders',      label: 'Orders',      sublabel: 'Daily order list',          filename: 'albertsons_orders.csv',       icon: '📦' },
  { key: 'locations',   label: 'Locations',   sublabel: 'DC + ~30 store locations',  filename: 'albertsons_locations.xlsx',   icon: '📍' },
  { key: 'constraints', label: 'Constraints', sublabel: 'Trailers, weights, costs',  filename: 'albertsons_constraints.xlsx', icon: '⚙️' },
] as const;

export interface ScenarioCatalogItem {
  key: string;
  label: string;
  blurb: string;
  highlights: string[];
}

export const sampleUrl = (key: string, scenario?: string) =>
  scenario
    ? `${BASE}/api/samples/${key}?scenario=${encodeURIComponent(scenario)}`
    : `${BASE}/api/samples/${key}`;

export async function getSampleCatalog(): Promise<{ scenarios: ScenarioCatalogItem[] }> {
  const r = await fetch(`${BASE}/api/samples/`);
  if (!r.ok) throw new Error(`samples catalog failed: ${await r.text()}`);
  return r.json();
}

export async function parseFiles(orders: File, locations: File, constraints: File) {
  const fd = new FormData();
  fd.append('orders', orders);
  fd.append('locations', locations);
  fd.append('constraints', constraints);
  const r = await fetch(`${BASE}/api/parse`, { method: 'POST', body: fd });
  if (!r.ok) throw new Error(`parse failed: ${await r.text()}`);
  return r.json();
}

export async function optimize(opts: { sessionId?: string; orders?: File; locations?: File; constraints?: File }): Promise<OptimizeResponse> {
  const fd = new FormData();
  if (opts.sessionId) fd.append('session_id', opts.sessionId);
  if (opts.orders) fd.append('orders', opts.orders);
  if (opts.locations) fd.append('locations', opts.locations);
  if (opts.constraints) fd.append('constraints', opts.constraints);
  const r = await fetch(`${BASE}/api/optimize`, { method: 'POST', body: fd });
  if (!r.ok) throw new Error(`optimize failed: ${await r.text()}`);
  return r.json();
}

export async function optimizeFromSamples(scenario?: string): Promise<OptimizeResponse> {
  const url = scenario
    ? `${BASE}/api/optimize-from-samples?scenario=${encodeURIComponent(scenario)}`
    : `${BASE}/api/optimize-from-samples`;
  const r = await fetch(url, { method: 'POST' });
  if (!r.ok) throw new Error(`optimize-from-samples failed: ${await r.text()}`);
  return r.json();
}

export async function reoptimize(sessionId: string, body: any) {
  const r = await fetch(`${BASE}/api/reoptimize/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`reoptimize failed: ${await r.text()}`);
  return r.json();
}

export async function explain(sessionId: string, routeId: string) {
  const r = await fetch(`${BASE}/api/explain/${sessionId}/${routeId}`);
  if (!r.ok) throw new Error(`explain failed: ${await r.text()}`);
  return r.json();
}

export async function validate(sessionId: string) {
  const r = await fetch(`${BASE}/api/validate/${sessionId}`, { method: 'POST' });
  if (!r.ok) throw new Error(`validate failed: ${await r.text()}`);
  return r.json();
}

export async function delayImpact(sessionId: string, routeId: string, delayMinutes: number) {
  const r = await fetch(`${BASE}/api/delay-impact/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ route_id: routeId, delay_minutes: delayMinutes }),
  });
  if (!r.ok) throw new Error(`delay-impact failed: ${await r.text()}`);
  return r.json();
}

export async function sensitivityLcv(sessionId: string, extraUnits: number, lcvConfig = 'SINGLE_53') {
  const r = await fetch(`${BASE}/api/sensitivity/lcv-availability/${sessionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ extra_lcv_units: extraUnits, lcv_trailer_config: lcvConfig }),
  });
  if (!r.ok) throw new Error(`sensitivity-lcv failed: ${await r.text()}`);
  return r.json();
}
