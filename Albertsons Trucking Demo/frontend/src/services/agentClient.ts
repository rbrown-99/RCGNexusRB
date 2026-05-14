/**
 * Lightweight rules-based "agent" so the demo runs end-to-end without an
 * Azure AI Foundry deployment. Recognizes intents like "what if", "drop X",
 * "explain R03", "how many splits", "delay R01 by 60 min", "snow in WY",
 * "what if I had 2 more SINGLE_53s", and translates them into apiClient calls.
 * Real deployments would replace this with a Foundry hosted-agent client.
 */
import * as api from './apiClient';
import type { OptimizeResponse, Route } from '../types';

export interface AgentReply {
  text: string;
  newResult?: OptimizeResponse;
}

export interface SuggestionChip {
  /** What the chip displays. */
  label: string;
  /** What gets sent through ask() when clicked (usually identical to label). */
  prompt: string;
}

/**
 * Per-scenario quick-action chips. Each set is hand-tuned so the chips
 * exercise the exception classes that scenario was designed to trigger.
 */
const SCENARIO_SUGGESTIONS: Record<string, SuggestionChip[]> = {
  standard_week: [
    { label: 'Explain my busiest route',         prompt: 'Explain my busiest route' },
    { label: 'What if we had +5% capacity?',     prompt: 'What if we had +5% capacity?' },
    { label: 'Show me low-utilization routes',   prompt: 'Show me low-utilization routes' },
    { label: 'Validate this plan',               prompt: 'Validate this plan' },
  ],
  heavy_volume: [
    { label: 'How many splits, and why?',        prompt: 'How many splits, and why?' },
    { label: 'What if I had 2 more SINGLE_53s?', prompt: 'What if I had 2 more SINGLE_53s?' },
    { label: 'Show me near-capacity routes',     prompt: 'Show me near-capacity routes' },
    { label: 'Snow in MT — restrict to SINGLE_53 there', prompt: 'Snow in MT — restrict to SINGLE_53 there' },
  ],
  tight_windows: [
    { label: 'Which routes are at risk of missing window?', prompt: 'Which routes are at risk of missing window?' },
    { label: 'What if windows had +90 min slack?',          prompt: 'What if windows had +90 min slack?' },
    { label: 'Delay my busiest route by 60 min — who misses?', prompt: 'Delay my busiest route by 60 minutes — who misses?' },
    { label: 'Validate this plan',                          prompt: 'Validate this plan' },
  ],
  long_haul_mix: [
    { label: 'Which routes need a layover?',              prompt: 'Which routes need a layover?' },
    { label: 'Show off-interstate doubles warnings',      prompt: 'Show off-interstate doubles warnings' },
    { label: 'Winter storm in WY — restrict to SINGLE_53 there', prompt: 'Winter storm in WY — restrict to SINGLE_53 there' },
    { label: 'Drop one 40-40 — what stays on doubles?',   prompt: 'Drop one 40-40 — what stays on doubles?' },
  ],
};

const DEFAULT_SUGGESTIONS_NO_RESULT: SuggestionChip[] = [
  { label: 'Run optimization with sample data', prompt: 'Run optimization with sample data' },
  { label: 'What can you do?',                  prompt: 'What can you do?' },
];

const DEFAULT_SUGGESTIONS_WITH_RESULT: SuggestionChip[] = [
  { label: 'Explain my busiest route',       prompt: 'Explain my busiest route' },
  { label: 'How many splits, and why?',      prompt: 'How many splits, and why?' },
  { label: 'Show me low-utilization routes', prompt: 'Show me low-utilization routes' },
  { label: 'Validate this plan',             prompt: 'Validate this plan' },
];

/**
 * Returns the chip set to render based on the loaded scenario + whether a
 * result is on screen. Pre-load: invite them to run the scenario. Post-load:
 * scenario-tuned chips.
 */
export function getSuggestions(opts: { scenario?: string; hasResult: boolean }): SuggestionChip[] {
  const fromScenario = opts.scenario && SCENARIO_SUGGESTIONS[opts.scenario];
  if (opts.hasResult && fromScenario) return fromScenario;
  if (opts.hasResult) return DEFAULT_SUGGESTIONS_WITH_RESULT;
  if (opts.scenario) {
    const scenarioName = opts.scenario.replace(/_/g, ' ');
    return [
      { label: `Run optimization on ${scenarioName}`, prompt: `Run optimization on ${scenarioName}` },
      { label: 'What can you do?',                    prompt: 'What can you do?' },
    ];
  }
  return DEFAULT_SUGGESTIONS_NO_RESULT;
}

function busiestRoute(result?: OptimizeResponse): Route | undefined {
  if (!result?.result?.routes?.length) return undefined;
  return [...result.result.routes].sort(
    (a, b) => (b.cube_utilization || 0) - (a.cube_utilization || 0),
  )[0];
}

function normalizeTrailerToken(t: string): string {
  const up = t.toUpperCase().replace(/\s/g, '_').replace(/S$/, '');
  if (up.includes('SINGLE') || /^53/.test(up)) return 'SINGLE_53';
  if (up === 'DOUBLE') return '40-40_COMBO';
  return `${up}_COMBO`;
}

export async function ask(
  prompt: string,
  ctx: { sessionId?: string; result?: OptimizeResponse },
): Promise<AgentReply> {
  const p = prompt.toLowerCase().trim();

  // -------- Help / capabilities --------
  if (/^(what can you do|help me|capabilities|commands|what.*help)/.test(p)) {
    return { text: helpText() };
  }

  // -------- Run optimization on a named scenario --------
  const scenarioMatch = p.match(/(?:run|optimize|plan|kick off|start|go|load)\s+(?:on |with |using |the )*?(standard\s*week|heavy\s*volume|tight\s*windows|long[\s-]?haul\s*mix)/);
  if (scenarioMatch) {
    const slug = scenarioMatch[1].replace(/[\s-]+/g, '_');
    const r = await api.optimizeFromSamples(slug);
    return { text: `Loaded **${slug.replace(/_/g, ' ')}** scenario.\n\n` + summarize(r), newResult: r };
  }
  if (/^(run|start|optimize|plan|go|kick off)/.test(p) || p.includes('sample')) {
    const r = await api.optimizeFromSamples();
    return { text: summarize(r), newResult: r };
  }

  // -------- Splits (Q8) --------
  if (/\bsplit/.test(p) && ctx.result) {
    return { text: splitsText(ctx.result) };
  }

  // -------- Sensitivity (Q20) — "+2 SINGLE_53s", "2 more 45-45s", "had 3 more 53s" --------
  const sensMatch = p.match(/(?:\+|add|more|extra|another|had)\s*(\d+)\s+(?:more\s+)?(40-40|45-45|48-28|single[_\s-]?53|single|53s?)/);
  if (sensMatch && ctx.sessionId) {
    const n = parseInt(sensMatch[1], 10);
    const cfg = normalizeTrailerToken(sensMatch[2]);
    const s = await api.sensitivityLcv(ctx.sessionId, n, cfg);
    return { text: sensitivityText(s, n, cfg) };
  }

  // -------- Weather override (Q21) — "snow/storm/winter ... in <ST> ... single 53" --------
  const weatherMention = /\b(snow|storm|weather|ice|winter|blizzard|whiteout)\b/.test(p);
  const single53Mention = /single[_\s-]?53|\b53s?\s*(?:only|ft)?\b/.test(p);
  const restrictMention = /restrict|only|just|allow|limit|restricted/.test(p);
  if (ctx.sessionId && weatherMention && (single53Mention || restrictMention)) {
    const stateRe = /\b([A-Z]{2})\b/g;
    const states: string[] = [];
    let m: RegExpExecArray | null;
    while ((m = stateRe.exec(prompt)) !== null) {
      const st = m[1];
      if (/^(MT|WY|ID|UT|NV|CO|NM|AZ|OR|WA|CA|ND|SD|NE|KS|MN|IA|MO|WI|IL|IN|OH|PA|NY|NJ|VA|NC|SC|GA|FL|AL|MS|LA|TX|OK|AR|TN|KY|WV|MD|DE|CT|RI|MA|NH|VT|ME|MI|AK|HI)$/.test(st)) {
        states.push(st);
      }
    }
    if (states.length) {
      const overrides: Record<string, string[]> = {};
      for (const s of states) overrides[s] = ['SINGLE_53'];
      const r: OptimizeResponse = await api.reoptimize(ctx.sessionId, {
        weather_overrides: overrides,
        extra_consideration: `Winter weather in ${states.join('/')} — restricted to SINGLE_53 only.`,
      });
      return {
        text: `Re-ran with **${states.join(', ')} restricted to SINGLE_53** (weather override).\n\n` + summarize(r),
        newResult: r,
      };
    }
  }

  // -------- Capacity relaxation (Q5) — "+5% capacity" --------
  const capMatch = p.match(/([+-]?\d+(?:\.\d+)?)\s*%\s*(?:more|extra|additional|of)?\s*(?:cube|weight|capacity|cap)/);
  if (capMatch && ctx.sessionId) {
    const pct = Math.abs(parseFloat(capMatch[1])) / 100;
    const r = await api.reoptimize(ctx.sessionId, { capacity_relaxation_pct: pct });
    return { text: `Re-ran with **+${(pct * 100).toFixed(0)}% capacity** on every trailer.\n\n` + summarize(r), newResult: r };
  }

  // -------- Window slack (Q6) — "+90 min slack" / "windows had 90 min" / "2 hr earlier or later" --------
  const slackMatch = p.match(/([+-]?\d+)\s*(min|m\b|minutes?|hr|h\b|hours?)\s*(?:of\s*)?(?:slack|earlier|later|window|wiggle)/)
    || p.match(/window[s]?\s+(?:had|with|of|at)\s*([+-]?\d+)\s*(min|m\b|minute|hr|h\b|hour)/);
  if (slackMatch && ctx.sessionId) {
    let n = Math.abs(parseInt(slackMatch[1], 10));
    if (/hr|hour/.test(slackMatch[2] || '')) n *= 60;
    const r = await api.reoptimize(ctx.sessionId, { window_slack_minutes: n });
    return { text: `Re-ran with **${n} minutes** of window slack on every store.\n\n` + summarize(r), newResult: r };
  }

  // -------- Hot load / priority first (Q11) --------
  const hotMatch = prompt.match(/(?:hot\s*load|priority|first stop)[^\w]*([A-Z]{3,4}-[A-Z]{2}-[A-Z0-9]{3,5})/i)
    || (/(hot\s*load|first stop|priority first)/i.test(p) ? prompt.match(/\b([A-Z]{3,4}-[A-Z]{2}-[A-Z0-9]{3,5})\b/) : null);
  if (hotMatch && ctx.sessionId) {
    const code = hotMatch[1];
    const r = await api.reoptimize(ctx.sessionId, { priority_first: [code] });
    return { text: `Re-ran with **${code}** as the first stop on its route.\n\n` + summarize(r), newResult: r };
  }

  // -------- Delay impact (Q7) — explicit route id --------
  const delayRouteMatch = prompt.match(/(?:delay|hold|holdup)\s+(R\d{2}-[\w-]+)\s+(?:by\s+)?(\d+)\s*(min|m\b|minute|hr|h\b|hour)/i);
  if (delayRouteMatch && ctx.sessionId) {
    let n = parseInt(delayRouteMatch[2], 10);
    if (/hr|hour/i.test(delayRouteMatch[3])) n *= 60;
    const di = await api.delayImpact(ctx.sessionId, delayRouteMatch[1], n);
    return { text: delayImpactText(di, delayRouteMatch[1], n) };
  }
  // -------- Delay impact — busiest/first/top route --------
  if (/delay\s+(?:my\s+)?(busiest|highest|biggest|first|top|fullest)/i.test(p) && ctx.sessionId) {
    const minutesMatch = p.match(/(\d+)\s*(min|m\b|minute|hr|h\b|hour)/);
    let n = minutesMatch ? parseInt(minutesMatch[1], 10) : 60;
    if (minutesMatch && /hr|hour/.test(minutesMatch[2])) n *= 60;
    const route = busiestRoute(ctx.result);
    if (!route) return { text: 'No routes loaded yet — run optimization first.' };
    const di = await api.delayImpact(ctx.sessionId, route.route_id, n);
    return { text: delayImpactText(di, route.route_id, n) };
  }

  // -------- Routes at risk of missing window (Q9) --------
  if (/(at[\s-]?risk|miss(?:ing)? window|window at risk|risk of missing)/.test(p) && ctx.result) {
    const ex = ctx.result.result.exceptions.filter((e) => e.code === 'WINDOW_AT_RISK' || e.code === 'DELIVERY_LATE');
    if (!ex.length) return { text: 'No routes are at risk of missing their window in this plan. ✅' };
    const grouped: Record<string, string[]> = {};
    for (const e of ex) {
      const rid = e.route_id || '(unassigned)';
      grouped[rid] = grouped[rid] || [];
      const tag = e.code === 'DELIVERY_LATE' ? '🔴 LATE' : '⚠️ at risk';
      grouped[rid].push(`${tag} ${e.location_code || ''} — ${e.message}`);
    }
    const lines = [`**${Object.keys(grouped).length} routes** with window risk:`, ''];
    for (const [rid, items] of Object.entries(grouped)) {
      lines.push(`**${rid}**`);
      for (const i of items) lines.push(`  • ${i}`);
    }
    return { text: lines.join('\n') };
  }

  // -------- Layover / HOS (Q17) --------
  if (/(layover|\bhos\b|hours? of service|sleep|overnight)/.test(p) && ctx.result) {
    const ex = ctx.result.result.exceptions.filter((e) => e.code === 'LAYOVER_REQUIRED' || e.code === 'DRIVER_HOURS_EXCEEDED');
    if (!ex.length) return { text: 'No routes need a layover in this plan. ✅' };
    const lines = [`**${ex.length} routes** flagged for layover / HOS:`, ''];
    for (const e of ex) lines.push(`• **${e.route_id}** — ${e.code}: ${e.message}`);
    return { text: lines.join('\n') };
  }

  // -------- Off-interstate doubles (Q16) --------
  if (/(off[\s-]?interstate|interstate|\blcb\b|doubles?\s+(warn|risk|off|issue))/.test(p) && ctx.result) {
    const ex = ctx.result.result.exceptions.filter((e) => e.code === 'LCB_OFF_INTERSTATE');
    if (!ex.length) return { text: 'No off-interstate warnings on doubles routes in this plan. ✅' };
    const lines = [`**${ex.length} off-interstate** warnings on doubles routes:`, ''];
    for (const e of ex) lines.push(`• **${e.route_id}** ${e.location_code || ''} — ${e.message}`);
    return { text: lines.join('\n') };
  }

  // -------- Suboptimal / low utilization / long inter-stop (Q4) --------
  if (/(suboptimal|low[\s-]?util|underutil|underloaded|long[\s-]?hop|long[\s-]?inter|consolidat)/.test(p) && ctx.result) {
    const ex = ctx.result.result.exceptions.filter((e) => e.code === 'LOW_UTILIZATION' || e.code === 'LONG_INTER_STOP_HOP');
    if (!ex.length) return { text: 'No suboptimal-route flags in this plan. ✅' };
    const lines = [`**${ex.length} suboptimal** flags:`, ''];
    for (const e of ex) lines.push(`• **${e.route_id}** ${e.code}: ${e.message}`);
    return { text: lines.join('\n') };
  }

  // -------- Near-capacity / over-capacity --------
  if (/(near[\s-]?cap|near capacity|over[\s-]?cap|over capacity|cube\s*near|weight\s*near|tight\s*cap)/.test(p) && ctx.result) {
    const ex = ctx.result.result.exceptions.filter((e) => /CUBE_(NEAR|OVER)|WEIGHT_(NEAR|OVER)/.test(e.code));
    if (!ex.length) return { text: 'No near- or over-capacity warnings in this plan. ✅' };
    const lines = [`**${ex.length} near/over-capacity** flags:`, ''];
    for (const e of ex) lines.push(`• **${e.route_id}** ${e.code}: ${e.message}`);
    return { text: lines.join('\n') };
  }

  // -------- Drop a trailer config (Q12) --------
  const trailerMatch = p.match(/(?:drop|remove|without|lose|no|down\s+a)\s+(?:a\s+|one\s+|the\s+)?(40-40|45-45|48-28|single[\s_]?53|single|double)/i);
  if (trailerMatch && ctx.sessionId) {
    const cfg = normalizeTrailerToken(trailerMatch[1]);
    const r: OptimizeResponse = await api.reoptimize(ctx.sessionId, { remove_trailer_configs: [cfg] });
    return { text: `Re-ran with **${cfg} unavailable**.\n\n` + summarize(r), newResult: r };
  }

  // -------- Drop a location code (Q10) --------
  const locMatch = prompt.match(/\b([A-Z]{3,4}-[A-Z]{2}-[A-Z0-9]{3,5})\b/);
  if (locMatch && /(drop|skip|remove|exclude|close)/i.test(p) && ctx.sessionId) {
    const r: OptimizeResponse = await api.reoptimize(ctx.sessionId, { remove_locations: [locMatch[1]] });
    return { text: `Re-ran with **${locMatch[1]} dropped**.\n\n` + summarize(r), newResult: r };
  }

  // -------- Explain busiest / first / top route --------
  if (/explain.*(busiest|highest|biggest|top|fullest|most loaded|first)/i.test(p) && ctx.sessionId) {
    const route = busiestRoute(ctx.result);
    if (!route) return { text: 'No routes loaded — run optimization first.' };
    const ex = await api.explain(ctx.sessionId, route.route_id);
    return { text: explainText(ex) };
  }

  // -------- Explain a specific route id --------
  const routeMatch = prompt.match(/\b(R\d{2}-[\w-]+)\b/i);
  if (routeMatch && ctx.sessionId) {
    const ex = await api.explain(ctx.sessionId, routeMatch[1]);
    return { text: explainText(ex) };
  }

  // -------- Validate --------
  if (/(validate|check.*plan|violation|verify)/.test(p) && ctx.sessionId) {
    const v = await api.validate(ctx.sessionId);
    return {
      text: `Validation: **${v.violations.length} violations**, ${v.warnings.length} warnings, ${v.info.length} info notes.\n` +
        v.violations.slice(0, 5).map((f: any) => `  • ${f.code}: ${f.message}`).join('\n'),
    };
  }

  // -------- Default --------
  if (ctx.result) return { text: summarize(ctx.result) };
  return { text: helpText() };
}

function helpText(): string {
  return [
    'I can:',
    '• **Run optimization** — load a sample scenario or use files you uploaded',
    '• **Explain** a route — *"explain R03-..."* or *"explain my busiest route"*',
    '• **Reoptimize** with a knob — capacity %, window slack, hot load, weather override, drop a trailer / store',
    '• **Delay impact** — *"delay R01 by 60 min"* or *"delay my busiest route by 60 min"*',
    '• **Sensitivity** — *"what if I had 2 more SINGLE_53s?"*',
    '• **Splits** — *"how many splits and why?"*',
    '• **Validate** the current plan',
    '',
    'Tap a chip below the input for one-click prompts tuned to the loaded scenario.',
  ].join('\n');
}

export function summarize(r: OptimizeResponse): string {
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

function splitsText(r: OptimizeResponse): string {
  const splits = r.result.splits || [];
  if (!splits.length) return 'No stores were split across routes in this plan. ✅';
  const lines = [`**${splits.length} stores** were split across multiple routes:`, ''];
  for (const s of splits) {
    const name = s.location_name ? ` (${s.location_name})` : '';
    const cases = s.total_cases ? `, ${s.total_cases} cases` : '';
    lines.push(`• **${s.location_code}**${name} on ${s.route_ids.length} routes — reason: *${s.reason}*`);
    lines.push(`    routes: ${s.route_ids.join(', ')}`);
    lines.push(`    total: ${s.total_weight_lbs.toFixed(0)} lbs, ${s.total_cube.toFixed(0)} cube${cases}`);
  }
  return lines.join('\n');
}

function sensitivityText(s: any, n: number, cfg: string): string {
  const d = s.delta || {};
  const lines = [
    `**Sensitivity: +${n} ${cfg} unit${n === 1 ? '' : 's'}**`,
    s.summary || '',
    '',
    `Cost: $${(s.scenario?.total_cost_usd ?? 0).toFixed(0)} (Δ $${(d.cost_usd || 0).toFixed(0)})`,
    `Routes: ${s.scenario?.total_routes ?? '?'} (Δ ${d.routes ?? 0})`,
    `Miles: ${(s.scenario?.total_miles ?? 0).toFixed(0)} (Δ ${(d.miles || 0).toFixed(0)})`,
    `${cfg} routes used: ${s.scenario?.lcv_routes_used ?? '?'} (Δ ${d.lcv_routes_used ?? 0})`,
  ];
  return lines.join('\n');
}

function delayImpactText(d: any, routeId: string, minutes: number): string {
  const newlyLate: string[] = d.newly_late_stops || [];
  const lines = [
    `**${routeId}** delayed by **${minutes} min**:`,
    d.summary || '',
    '',
  ];
  if (!newlyLate.length) {
    lines.push(`✅ No newly-late stops — every store still hits its window.`);
  } else {
    lines.push(`🔴 **${newlyLate.length} newly-late stops:** ${newlyLate.join(', ')}`);
  }
  return lines.join('\n');
}
