import type { ExceptionItem } from '../types';

export default function ExceptionsPanel({ items }: { items: ExceptionItem[] }) {
  if (!items.length) return <div className="exceptions empty">No findings.</div>;
  const order = { VIOLATION: 0, WARNING: 1, INFO: 2 } as const;
  const sorted = [...items].sort((a, b) => order[a.severity] - order[b.severity]);
  return (
    <div className="exceptions">
      <h4>Exceptions ({items.length})</h4>
      <ul>
        {sorted.map((e, i) => (
          <li key={i} className={`sev-${e.severity.toLowerCase()}`}>
            <strong>{e.severity}</strong> · {e.code}
            {e.route_id && <> · <em>{e.route_id}</em></>}
            <div>{e.message}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
