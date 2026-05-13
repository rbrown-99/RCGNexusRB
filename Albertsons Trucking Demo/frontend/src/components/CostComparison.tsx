import type { OptimizationResult } from '../types';

export default function CostComparison({ result }: { result: OptimizationResult }) {
  const { naive_baseline, total_cost_usd, total_miles, total_routes, savings_usd, savings_percent } = result;
  return (
    <div className="cost-compare">
      <h4>Cost comparison</h4>
      <table>
        <thead><tr><th></th><th>Optimized</th><th>Naive baseline</th><th>Δ</th></tr></thead>
        <tbody>
          <tr><td>Routes</td><td>{total_routes}</td><td>{naive_baseline.total_routes}</td><td>{total_routes - naive_baseline.total_routes}</td></tr>
          <tr><td>Miles</td><td>{total_miles.toFixed(0)}</td><td>{naive_baseline.total_miles.toFixed(0)}</td><td>{(total_miles - naive_baseline.total_miles).toFixed(0)}</td></tr>
          <tr><td>Cost</td><td>${total_cost_usd.toFixed(0)}</td><td>${naive_baseline.total_cost_usd.toFixed(0)}</td><td className={savings_usd >= 0 ? 'savings' : 'loss'}>${(-savings_usd).toFixed(0)} ({savings_percent.toFixed(1)}%)</td></tr>
        </tbody>
      </table>
    </div>
  );
}
