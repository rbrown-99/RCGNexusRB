import { useState } from 'react';
import { parseFiles, optimize } from '../services/apiClient';
import type { OptimizeResponse } from '../types';

interface Props {
  onResult: (r: OptimizeResponse) => void;
  onSession: (sid: string) => void;
}

export default function FileUpload({ onResult, onSession }: Props) {
  const [orders, setOrders] = useState<File | null>(null);
  const [locations, setLocations] = useState<File | null>(null);
  const [constraints, setConstraints] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const ready = orders && locations && constraints;

  async function go() {
    if (!ready) return;
    setBusy(true);
    setErr(null);
    try {
      const parsed = await parseFiles(orders!, locations!, constraints!);
      onSession(parsed.session_id);
      const r = await optimize({ sessionId: parsed.session_id });
      onResult(r);
    } catch (e: any) {
      setErr(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="upload">
      <h3>Upload your files</h3>
      <label>Orders (CSV/XLSX) <input type="file" accept=".csv,.xlsx" onChange={(e) => setOrders(e.target.files?.[0] || null)} /></label>
      <label>Locations (XLSX) <input type="file" accept=".xlsx" onChange={(e) => setLocations(e.target.files?.[0] || null)} /></label>
      <label>Constraints (XLSX) <input type="file" accept=".xlsx" onChange={(e) => setConstraints(e.target.files?.[0] || null)} /></label>
      <button disabled={!ready || busy} onClick={go}>
        {busy ? 'Optimizing…' : 'Parse + Optimize'}
      </button>
      {err && <div className="err">{err}</div>}
    </div>
  );
}
