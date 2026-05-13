import type { OptimizationResult } from '../types';

interface Props {
  result: OptimizationResult;
}

function fmtMoney(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
}

export default function KpiCards({ result }: Props) {
  const onTime = result.routes.filter(r => r.on_time).length;
  const total = result.routes.length;
  const exceptions = result.exceptions.length;

  const cards = [
    { label: 'Routes',        value: total.toString(),                    sub: `${onTime} on-time / ${total - onTime} flagged` },
    { label: 'Total miles',   value: result.total_miles.toLocaleString('en-US', { maximumFractionDigits: 0 }),
                              sub: 'across all dispatched trucks' },
    { label: 'Total cost',    value: fmtMoney(result.total_cost_usd),     sub: 'per-mile + per-stop' },
    { label: 'Savings',       value: `${result.savings_percent.toFixed(1)}%`,
                              sub: `${fmtMoney(result.savings_usd)} vs. naive baseline`,
                              good: result.savings_percent > 0 },
    { label: 'Cube fill',     value: `${(result.average_cube_utilization * 100).toFixed(0)}%`,
                              sub: 'average trailer cube utilization' },
    { label: 'Exceptions',    value: exceptions.toString(),
                              sub: exceptions === 0 ? 'no issues to review' : 'see panel below',
                              warn: exceptions > 0 },
  ];

  return (
    <div className="kpis">
      {cards.map(c => (
        <div key={c.label} className={`kpi ${c.good ? 'kpi-good' : ''} ${c.warn ? 'kpi-warn' : ''}`}>
          <div className="kpi-value">{c.value}</div>
          <div className="kpi-label">{c.label}</div>
          <div className="kpi-sub">{c.sub}</div>
        </div>
      ))}
    </div>
  );
}
