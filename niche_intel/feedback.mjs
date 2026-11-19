// niche_intel/feedback.mjs - weekly performance learning loop.
// Input: YouTube Analytics API via OAuth when available in secrets, OR a CSV
// the owner exports from YouTube Studio into feedback/inbox/. Proposes small
// weight adjustments (max +/-10% per weight per week) as a PR for review -
// NEVER auto-merged. No conclusions from small samples (<10 videos).
import {readFile, readdir} from 'node:fs/promises';
import path from 'node:path';

export const MIN_SAMPLE = 10;
export const MAX_WEEKLY_SHIFT = 0.10; // 10% of the weight per week

// Expected CSV columns from a YouTube Studio export (Arabic or English UI):
// Video title, Views, Average view duration, Average percentage viewed,
// Subscribers gained, plus our side-join to state/niche picks for pillar.
export async function loadPerformanceCsv(dir = 'feedback/inbox') {
  let files = [];
  try { files = (await readdir(dir)).filter(f => f.endsWith('.csv')).sort(); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  const rows = [];
  for (const f of files) {
    const text = await readFile(path.join(dir, f), 'utf8');
    const lines = text.split(/\r?\n/).filter(Boolean);
    const head = lines.shift()?.toLowerCase() || '';
    const delim = head.split(';').length > head.split(',').length ? ';' : ',';
    const cols = head.split(delim).map(c => c.trim());
    const idx = names => names.map(n => cols.findIndex(c => c.includes(n))).find(i => i >= 0) ?? -1;
    const iTitle = idx(['video title', 'عنوان الفيديو']), iViews = idx(['views', 'المشاهدات']), iAvgView = idx(['average percentage viewed', 'متوسط النسبة المئوية للمشاهدة']);
    for (const line of lines) {
      const c = line.split(delim).map(x => x.trim().replace(/^"|"$/g, ''));
      const views = Number(c[iViews]); const pct = parseFloat(c[iAvgView]);
      if (c[iTitle] && Number.isFinite(views)) rows.push({title: c[iTitle], views, avgPctViewed: Number.isFinite(pct) ? pct : null, file: f});
    }
  }
  return rows;
}

export function proposeWeightChanges(perf, picks, weights) {
  if (perf.length < MIN_SAMPLE) return {ok: false, reason: 'sample_too_small', sample: perf.length, min: MIN_SAMPLE, note: 'no conclusions drawn from small samples'};
  const med = [...perf.map(p => p.views)].sort((a, b) => a - b)[Math.floor(perf.length / 2)];
  const joined = perf.map(p => ({...p, pick: picks.find(k => k.title === p.title)})).filter(p => p.pick?.components);
  if (joined.length < MIN_SAMPLE) return {ok: false, reason: 'unmatched_titles', matched: joined.length, note: 'CSV titles must match state/niche picks to attribute performance'};
  const winners = joined.filter(p => p.views >= med), losers = joined.filter(p => p.views < med);
  const avg = (rows, k) => rows.length ? rows.reduce((s, r) => s + (r.pick.components[k] || 0), 0) / rows.length : null;
  const proposal = {};
  for (const k of ['demand', 'gap', 'trend', 'fit', 'visual', 'hook']) {
    const wAvg = avg(winners, k), lAvg = avg(losers, k);
    if (wAvg === null || lAvg === null) continue;
    const direction = wAvg > lAvg ? 1 : wAvg < lAvg ? -1 : 0;
    const delta = Math.round(weights[k] * MAX_WEEKLY_SHIFT) * direction; // bounded per week
    if (delta !== 0) proposal[k] = {from: weights[k], to: weights[k] + delta, evidence: 'winners avg ' + wAvg.toFixed(2) + ' vs losers ' + lAvg.toFixed(2)};
  }
  return {ok: true, proposal, sample: joined.length, medianViews: med};
}

export function weeklyInsightsMd(result, generatedAt = new Date().toISOString()) {
  const lines = ['# Weekly Insights', '', '_Generated ' + generatedAt + '_', ''];
  if (!result.ok) { lines.push('No weight changes this week: ' + result.reason + ' (' + (result.note || 'insufficient data') + ').'); return lines.join('\n') + '\n'; }
  lines.push('Sample: ' + result.sample + ' videos, median views ' + result.medianViews + '.', '');
  const entries = Object.entries(result.proposal);
  if (!entries.length) lines.push('No component separates winners from losers this week; weights unchanged.');
  for (const [k, p] of entries) lines.push('- `' + k + '`: ' + p.from + ' -> ' + p.to + ' (' + p.evidence + ')');
  lines.push('', 'Proposals are review-only: a human merges the weekly PR or closes it.');
  return lines.join('\n') + '\n';
}
