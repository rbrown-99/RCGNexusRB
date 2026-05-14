import type { Route, ExceptionItem } from '../types';

interface Props {
  routes: Route[];
  exceptions?: ExceptionItem[];
}

export default function RouteSummaryTable({ routes, exceptions = [] }: Props) {
  // Build per-route flag set so we can show "at risk" / "layover" pills inline.
  const flagsByRoute: Record<string, { atRisk: boolean; layover: boolean; offInterstate: boolean; lowUtil: boolean }> = {};
  for (const r of routes) {
    flagsByRoute[r.route_id] = { atRisk: false, layover: false, offInterstate: false, lowUtil: false };
  }
  for (const e of exceptions) {
    if (!e.route_id || !flagsByRoute[e.route_id]) continue;
    if (e.code === 'WINDOW_AT_RISK' || e.code === 'DELIVERY_LATE') flagsByRoute[e.route_id].atRisk = true;
    if (e.code === 'LAYOVER_REQUIRED' || e.code === 'LAYOVER_SUGGESTED' || e.code === 'DRIVER_HOURS_EXCEEDED') flagsByRoute[e.route_id].layover = true;
    if (e.code === 'LCB_OFF_INTERSTATE') flagsByRoute[e.route_id].offInterstate = true;
    if (e.code === 'LOW_UTILIZATION') flagsByRoute[e.route_id].lowUtil = true;
  }

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
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {routes.map((r) => {
            const f = flagsByRoute[r.route_id];
            return (
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
                <td className="route-status-cell">
                  <div className="route-status-stack">
                    <span className={`status-pill ${r.on_time ? 'status-ok' : 'status-late'}`}>
                      {r.on_time ? 'On time' : 'Late'}
                    </span>
                    {f.atRisk && r.on_time && (
                      <span className="status-pill status-warn" title="One or more stops arrive close to window close">
                        Window risk
                      </span>
                    )}
                    {f.layover && (
                      <span className="status-pill status-violation" title="Driver hours close to or over the HOS cap">
                        Layover
                      </span>
                    )}
                    {f.offInterstate && (
                      <span className="status-pill status-warn" title="LCB combo with multiple stops in an interstate-only state">
                        Off-IS
                      </span>
                    )}
                    {f.lowUtil && (
                      <span className="status-pill status-info" title="Both weight and cube utilization below 55%">
                        Low util
                      </span>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
