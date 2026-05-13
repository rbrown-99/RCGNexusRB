import { SAMPLE_FILES, sampleUrl } from '../services/apiClient';

interface Props {
  onRunSample: () => void;
  busy: boolean;
}

/**
 * Business-user-friendly panel that:
 *  1. Lets the dispatcher download the three sample input files (so they
 *     can see exactly what the system expects, edit a row, and re-upload).
 *  2. Offers one-click "Try with sample data" to run the demo end-to-end.
 */
export default function SampleDownloads({ onRunSample, busy }: Props) {
  return (
    <div className="samples">
      <h3>Sample dataset</h3>
      <p className="samples-help">
        Download the three example files below to see the format the system expects.
        Edit them, re-upload, or run the optimizer with the samples directly.
      </p>
      <div className="samples-list">
        {SAMPLE_FILES.map(s => (
          <a
            key={s.key}
            className="sample-card"
            href={sampleUrl(s.key)}
            download={s.filename}
            title={`Download ${s.filename}`}
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
      <button className="primary-cta" disabled={busy} onClick={onRunSample}>
        {busy ? (
          <><span className="spinner" /> Optimizing routes…</>
        ) : (
          <>▶ Try it with sample data</>
        )}
      </button>
      <p className="samples-foot">No data setup required — runs end-to-end in seconds.</p>
    </div>
  );
}
