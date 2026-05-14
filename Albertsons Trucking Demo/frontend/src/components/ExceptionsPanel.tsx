import type { ExceptionItem } from '../types';
import { useMemo, useState } from 'react';

const SEVERITY_ORDER = { VIOLATION: 0, WARNING: 1, INFO: 2 } as const;

const CODE_LABEL: Record<string, string> = {
  MAX_STOPS_EXCEEDED: 'Stops over trailer max',
  CUBE_OVER_CAPACITY: 'Cube over capacity',
  CUBE_NEAR_CAPACITY: 'Cube near capacity',
  WEIGHT_OVER_CAPACITY: 'Weight over capacity',
  WEIGHT_NEAR_CAPACITY: 'Weight near capacity',
  DELIVERY_LATE: 'Delivery late',
  WINDOW_AT_RISK: 'Window at risk',
  LOW_UTILIZATION: 'Low utilization',
  LONG_INTER_STOP_HOP: 'Long inter-stop hop',
  LCB_OFF_INTERSTATE: 'Off-interstate combo',
  LAYOVER_REQUIRED: 'Layover required',
  LAYOVER_SUGGESTED: 'Layover suggested',
  DRIVER_HOURS_EXCEEDED: 'Driver hours exceeded',
  ROAD_RESTRICTION_NOTE: 'Road restriction',
  NO_SOLUTION: 'No feasible solution',
};

export default function ExceptionsPanel({ items }: { items: ExceptionItem[] }) {
  const [activeFilter, setActiveFilter] = useState<'ALL' | 'VIOLATION' | 'WARNING' | 'INFO'>('ALL');

  const counts = useMemo(() => {
    const c = { VIOLATION: 0, WARNING: 0, INFO: 0 };
    for (const e of items) c[e.severity]++;
    return c;
  }, [items]);

  if (!items.length) {
    return (
      <div className="exceptions exceptions-card empty">
        <h4>Exceptions</h4>
        <div className="exceptions-empty-msg">
          <span className="exceptions-empty-check">✓</span>
          <span>No findings — every route is within capacity, on time, and inside HOS.</span>
        </div>
      </div>
    );
  }

  const filtered = activeFilter === 'ALL'
    ? items
    : items.filter((e) => e.severity === activeFilter);
  const sorted = [...filtered].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  );

  return (
    <div className="exceptions exceptions-card">
      <div className="exceptions-header">
        <h4>Exceptions ({items.length})</h4>
        <div className="exceptions-filter" role="tablist">
          <FilterChip
            label={`All ${items.length}`}
            active={activeFilter === 'ALL'}
            onClick={() => setActiveFilter('ALL')}
            kind="all"
          />
          <FilterChip
            label={`Violations ${counts.VIOLATION}`}
            active={activeFilter === 'VIOLATION'}
            onClick={() => setActiveFilter('VIOLATION')}
            kind="violation"
            disabled={counts.VIOLATION === 0}
          />
          <FilterChip
            label={`Warnings ${counts.WARNING}`}
            active={activeFilter === 'WARNING'}
            onClick={() => setActiveFilter('WARNING')}
            kind="warning"
            disabled={counts.WARNING === 0}
          />
          <FilterChip
            label={`Info ${counts.INFO}`}
            active={activeFilter === 'INFO'}
            onClick={() => setActiveFilter('INFO')}
            kind="info"
            disabled={counts.INFO === 0}
          />
        </div>
      </div>
      <ul>
        {sorted.map((e, i) => (
          <li key={i} className={`sev-${e.severity.toLowerCase()}`}>
            <div className="exception-row-top">
              <span className={`sev-tag sev-tag-${e.severity.toLowerCase()}`}>{e.severity}</span>
              <span className="exception-label">{CODE_LABEL[e.code] || e.code}</span>
              {e.route_id && <span className="exception-route">{e.route_id}</span>}
              {e.location_code && <span className="exception-loc">{e.location_code}</span>}
            </div>
            <div className="exception-msg">{e.message}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface FilterChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
  kind: 'all' | 'violation' | 'warning' | 'info';
  disabled?: boolean;
}

function FilterChip({ label, active, onClick, kind, disabled }: FilterChipProps) {
  return (
    <button
      type="button"
      className={`filter-chip filter-chip-${kind} ${active ? 'active' : ''}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}
