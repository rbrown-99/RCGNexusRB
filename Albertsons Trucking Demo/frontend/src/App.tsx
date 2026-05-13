import { useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import RouteMap from './components/RouteMap';
import RouteSummaryTable from './components/RouteSummaryTable';
import ExceptionsPanel from './components/ExceptionsPanel';
import ConsiderationsPanel from './components/ConsiderationsPanel';
import CostComparison from './components/CostComparison';
import { optimizeFromSamples } from './services/apiClient';
import type { OptimizeResponse } from './types';
import './app.css';

export default function App() {
  const [resp, setResp] = useState<OptimizeResponse | undefined>();
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  async function runSample() {
    setBusy(true);
    try {
      const r = await optimizeFromSamples();
      setResp(r);
      setSessionId(r.session_id);
    } catch (e: any) {
      alert(e.message || e);
    } finally {
      setBusy(false);
    }
  }

  function handleResult(r: OptimizeResponse) {
    setResp(r);
    setSessionId(r.session_id);
  }

  return (
    <div className="app">
      <header>
        <h1>Albertsons Truck Routing</h1>
        <button onClick={runSample} disabled={busy}>
          {busy ? 'Running…' : 'Run sample dataset'}
        </button>
      </header>

      <div className="grid">
        <aside className="left">
          <FileUpload onResult={handleResult} onSession={setSessionId} />
          <ChatInterface sessionId={sessionId} result={resp} onResult={handleResult} />
        </aside>

        <main className="right">
          {resp ? (
            <>
              <CostComparison result={resp.result} />
              <RouteMap routes={resp.result.routes} />
              <RouteSummaryTable routes={resp.result.routes} />
              <div className="two-col">
                <ConsiderationsPanel items={resp.result.considerations} relaxed={resp.result.relaxed_constraints} />
                <ExceptionsPanel items={resp.result.exceptions} />
              </div>
              {resp.distance_source === 'haversine_fallback' && (
                <div className="note">Using haversine fallback for distances. Set <code>AZURE_MAPS_KEY</code> for truck-routed mileage.</div>
              )}
            </>
          ) : (
            <div className="placeholder">Upload files or click <em>Run sample dataset</em> to begin.</div>
          )}
        </main>
      </div>
    </div>
  );
}
