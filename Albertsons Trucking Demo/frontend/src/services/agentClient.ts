/**
 * Lightweight rules-based "agent" so the demo runs end-to-end without an
 * Azure AI Foundry deployment. Recognizes intents like "what if", "drop X",
 * "explain R03", and translates them into apiClient calls. Real deployments
 * would replace this with a Foundry hosted-agent client.
 */
import * as api from './apiClient';
import type { OptimizeResponse } from '../types';

export interface AgentReply {
  text: string;
  newResult?: OptimizeResponse;
}

export async function ask(
  prompt: string,
  ctx: { sessionId?: string; result?: OptimizeResponse },
): Promise<AgentReply> {
  const p = prompt.toLowerCase().trim();

  // Optimize fresh from samples
  if (/^(run|start|optimize|plan|go|kick off)/.test(p) || p.includes('sample')) {
    const r = await api.optimizeFromSamples();
    return {
      text: summarize(r),
      newResult: r,
    };
  }

  // Drop trailer config
  const trailerMatch = p.match(/(?:drop|remove|without|lose|no)\s+(40-40|45-45|48-28|single[\s_]?53|single)/i);
  if (trailerMatch && ctx.sessionId) {
    const t = trailerMatch[1].toUpperCase().replace(/\s/g, '_');
    const cfg = t.includes('SINGLE') ? 'SINGLE_53' : `${t}_COMBO`;
    const r: OptimizeResponse = await api.reoptimize(ctx.sessionId, { remove_trailer_configs: [cfg] });
    return { text: `Re-ran with ${cfg} unavailable.\n\n` + summarize(r), newResult: r };
  }

  // Drop a location code
  const locMatch = prompt.match(/\b([A-Z]{3,4}-[A-Z]{2}-[A-Z0-9]{3,5})\b/);
  if (locMatch && /(drop|skip|remove|exclude)/i.test(p) && ctx.sessionId) {
    const r: OptimizeResponse = await api.reoptimize(ctx.sessionId, { remove_locations: [locMatch[1]] });
    return { text: `Re-ran with ${locMatch[1]} dropped.\n\n` + summarize(r), newResult: r };
  }

  // Explain a route
  const routeMatch = prompt.match(/\b(R\d{2}-[\w-]+)\b/i);
  if (routeMatch && ctx.sessionId) {
    const ex = await api.explain(ctx.sessionId, routeMatch[1]);
    return { text: explainText(ex) };
  }

  // Validate
  if (/(validate|check|violation)/.test(p) && ctx.sessionId) {
    const v = await api.validate(ctx.sessionId);
    return {
      text: `Validation: ${v.violations.length} violations, ${v.warnings.length} warnings, ${v.info.length} info notes.\n` +
        v.violations.slice(0, 5).map((f: any) => `  • ${f.code}: ${f.message}`).join('\n'),
    };
  }

  // Default: summarize current result
  if (ctx.result) {
    return { text: summarize(ctx.result) };
  }

  return {
    text: 'Try: "run optimization", "what if we lose 45-45 trailers", "drop ALB-MT-MISA", "explain R03-...", "validate".',
  };
}

function summarize(r: OptimizeResponse): string {
  const res = r.result;
  const lines = [
    `**${res.total_routes} routes**, ${res.total_miles.toFixed(0)} miles, $${res.total_cost_usd.toFixed(0)} cost.`,
    `Naive baseline: $${res.naive_baseline.total_cost_usd.toFixed(0)} → savings **${res.savings_percent.toFixed(1)}%** ($${res.savings_usd.toFixed(0)}).`,
    `Avg cube util ${(res.average_cube_utilization * 100).toFixed(0)}%, weight util ${(res.average_weight_utilization * 100).toFixed(0)}%.`,
    `Solved in ${res.solve_seconds}s (${res.solver_status}).`,
  ];
  const v = res.exceptions.filter((e) => e.severity === 'VIOLATION');
  if (v.length) lines.push(`⚠️ **${v.length} violations** — review the Exceptions panel.`);
  if (r.distance_source === 'haversine_fallback') {
    lines.push('_Mileage approximate (haversine). Set AZURE_MAPS_KEY for truck-routed distances._');
  }
  return lines.join('\n');
}

function explainText(ex: any): string {
  const lines = [
    `**${ex.route_id}** — ${ex.trailer_config}, ${ex.temperature_group}, ${ex.stop_count} stops.`,
    `${ex.total_miles} miles • $${ex.estimated_cost_usd} • states: ${ex.states_traversed.join(', ')}.`,
    `Weight ${ex.weight_lbs} / ${ex.weight_capacity_lbs_effective} lbs (${ex.weight_utilization_pct}%). ` +
      `Cube ${ex.cube} / ${ex.cube_capacity_effective} (${ex.cube_utilization_pct}%).`,
  ];
  for (const r of ex.rationale.filter(Boolean)) lines.push(`• ${r}`);
  return lines.join('\n');
}
