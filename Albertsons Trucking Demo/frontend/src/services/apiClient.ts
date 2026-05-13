import type { OptimizeResponse } from '../types';

export const BASE = (import.meta.env.VITE_BACKEND_URL as string) || 'http://localhost:8000';

export const SAMPLE_FILES = [
  { key: 'orders',      label: 'Orders',      sublabel: '100 orders across 30 stores', filename: 'albertsons_sample_orders.csv',       icon: '📦' },
  { key: 'locations',   label: 'Locations',   sublabel: 'DC + 30 store locations',     filename: 'albertsons_sample_locations.xlsx',   icon: '📍' },
  { key: 'constraints', label: 'Constraints', sublabel: 'Trailers, weights, costs',    filename: 'albertsons_sample_constraints.xlsx', icon: '⚙️' },
] as const;

export const sampleUrl = (key: string) => `${BASE}/api/samples/${key}`;

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

export async function optimizeFromSamples(): Promise<OptimizeResponse> {
  const r = await fetch(`${BASE}/api/optimize-from-samples`, { method: 'POST' });
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
