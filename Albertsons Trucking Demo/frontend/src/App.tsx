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
import DelayImpactPanel from './components/DelayImpactPanel';
import SensitivityPanel from './components/SensitivityPanel';
import ArchitecturePage from './components/ArchitecturePage';
import GuidePage from './components/GuidePage';
import BrandLogo from './components/BrandLogo';
import { optimizeFromSamples } from './services/apiClient';
import type { OptimizeResponse } from './types';
import './app.css';

type Tab = 'optimizer' | 'architecture' | 'guide';

export default function App() {
  const [resp, setResp] = useState<OptimizeResponse | undefined>();
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState<Tab>('optimizer');
  const [lastRunScenario, setLastRunScenario] = useState<string | undefined>();

  async function runSample(scenario: string) {
    setBusy(true);
    try {
      const r = await optimizeFromSamples(scenario);
      setResp(r);
      setSessionId(r.session_id);
      setLastRunScenario(scenario);
    } catch (e: any) {
      alert(e.message || e);
    } finally {
      setBusy(false);
    }
  }

  function handleResult(r: OptimizeResponse) {
    setResp(r);
    setSessionId(r.session_id);
    // Uploads/reoptimize don't carry a "scenario" tag; clear it so the picker
    // hint doesn't lie.
    setLastRunScenario(r.scenario);
  }

  const tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'optimizer',    label: 'Optimizer',    icon: '🚛' },
    { id: 'architecture', label: 'Architecture', icon: '🏗️' },
    { id: 'guide',        label: 'Guide',        icon: '📖' },
  ];

  return (
    <div className="app">
      <div className="brand-bar" aria-hidden />
      <header>
        <div className="brand">
          <BrandLogo height={42} />
          <span className="brand-tag">SLC Distribution Center · Route Optimization</span>
        </div>
        <nav className="tab-nav">
          {tabs.map((t) => (
            <button
              key={t.id}
              className={`tab-btn ${tab === t.id ? 'active' : ''}`}
              onClick={() => setTab(t.id)}
            >
              <span className="tab-icon" aria-hidden>{t.icon}</span> {t.label}
            </button>
          ))}
        </nav>
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

      {tab === 'optimizer' && (
        <div className="grid">
          <aside className="left">
            <SampleDownloads
              onRunSample={runSample}
              busy={busy}
              lastRunScenario={lastRunScenario}
            />
            <FileUpload onResult={handleResult} onSession={setSessionId} />
            <ChatInterface sessionId={sessionId} result={resp} onResult={handleResult} />
          </aside>

          <main className="right">
            {resp ? (
              <>
                <KpiCards result={resp.result} />
                <CostComparison result={resp.result} />
                <RouteMap routes={resp.result.routes} />
                <RouteSummaryTable routes={resp.result.routes} exceptions={resp.result.exceptions} />
                <div className="two-col">
                  <ConsiderationsPanel
                    items={resp.result.considerations}
                    relaxed={resp.result.relaxed_constraints}
                  />
                  <ExceptionsPanel items={resp.result.exceptions} />
                </div>
                <div className="two-col">
                  <DelayImpactPanel sessionId={sessionId} routes={resp.result.routes} />
                  <SensitivityPanel sessionId={sessionId} routes={resp.result.routes} />
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
      )}

      {tab === 'architecture' && (
        <main className="single-pane">
          <ArchitecturePage />
        </main>
      )}

      {tab === 'guide' && (
        <main className="single-pane">
          <GuidePage />
        </main>
      )}

      <footer>
        <span>Albertsons Companies — Logistics Demo</span>
      </footer>
    </div>
  );
}
