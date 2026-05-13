import { useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import RouteMap from './components/RouteMap';
import RouteSummaryTable from './components/RouteSummaryTable';
import ExceptionsPanel from './components/ExceptionsPanel';
import ConsiderationsPanel from './components/ConsiderationsPanel';
import CostComparison from './components/CostComparison';
import KpiCards from './components/KpiCards';
import WelcomeCard from './components/WelcomeCard';
import SampleDownloads from './components/SampleDownloads';
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
        <div className="brand">
          <span className="brand-mark" aria-hidden>A</span>
          <div className="brand-text">
            <span className="brand-name">Albertsons</span>
            <span className="brand-tag">SLC Distribution Center · Route Optimization</span>
          </div>
        </div>
        <div className="header-actions">
          <span className="header-status">
            {resp ? (
              <><span className="dot dot-ok" /> {resp.result.routes.length} routes loaded</>
            ) : (
              <><span className="dot dot-idle" /> Ready</>
            )}
          </span>
        </div>
      </header>

      <div className="grid">
        <aside className="left">
          <SampleDownloads onRunSample={runSample} busy={busy} />
          <FileUpload onResult={handleResult} onSession={setSessionId} />
          <ChatInterface sessionId={sessionId} result={resp} onResult={handleResult} />
        </aside>

        <main className="right">
          {resp ? (
            <>
              <KpiCards result={resp.result} />
              <CostComparison result={resp.result} />
              <RouteMap routes={resp.result.routes} />
              <RouteSummaryTable routes={resp.result.routes} />
              <div className="two-col">
                <ConsiderationsPanel
                  items={resp.result.considerations}
                  relaxed={resp.result.relaxed_constraints}
                />
                <ExceptionsPanel items={resp.result.exceptions} />
              </div>
              {resp.distance_source === 'haversine_fallback' && (
                <div className="note">
                  Distance fallback: this run used straight-line distances.
                  Set <code>AZURE_MAPS_KEY</code> in the backend to enable
                  truck-routed mileage.
                </div>
              )}
            </>
          ) : (
            <WelcomeCard />
          )}
        </main>
      </div>

      <footer>
        <span>Albertsons Companies — Logistics Demo</span>
        <span className="foot-sep">·</span>
        <span>Cold-chain VRP solver powered by Google OR-Tools</span>
      </footer>
    </div>
  );
}
