import type { Route } from '../types';

export default function RouteSummaryTable({ routes }: { routes: Route[] }) {
  return (
    <div className="route-table">
      <table>
        <thead>
          <tr>
            <th>Route</th>
            <th>Trailer</th>
            <th>Temp</th>
            <th>Stops</th>
            <th>Miles</th>
            <th>Hrs</th>
            <th>Weight%</th>
            <th>Cube%</th>
            <th>Cost</th>
            <th>States</th>
            <th>On-time</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((r) => (
            <tr key={r.route_id}>
              <td>{r.route_id}</td>
              <td>{r.trailer_config}</td>
              <td>{r.temperature_group}</td>
              <td>{r.stops.length}</td>
              <td>{r.total_miles.toFixed(0)}</td>
              <td>{(r.total_minutes / 60).toFixed(1)}</td>
              <td>{(r.weight_utilization * 100).toFixed(0)}%</td>
              <td>{(r.cube_utilization * 100).toFixed(0)}%</td>
              <td>${r.estimated_cost_usd.toFixed(0)}</td>
              <td>{r.states_traversed.join(', ')}</td>
              <td>{r.on_time ? '✓' : '✗'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
