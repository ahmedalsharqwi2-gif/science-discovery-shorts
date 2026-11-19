// niche_intel/competition.mjs - competition and opportunity-gap measurement.
// Needs YouTube Data API (official). Without the key every metric is unknown
// and the caller degrades the score with a warning, per owner rule 1/3.
export function median(nums) {
  const a = nums.filter(n => Number.isFinite(n)).sort((x, y) => x - y);
  return a.length ? a[Math.floor(a.length / 2)] : null;
}

// Outlier: small channel (< smallChannelSubs) whose video views > 10x subs.
// Presence of outliers is evidence of un-monopolized demand.
export function analyzeCompetition(videos, {smallChannelSubs = 50000, outlierMultiple = 10, now = Date.now()} = {}) {
  if (!Array.isArray(videos)) return {status: 'unknown', reason: 'no YouTube data (missing key or fetch failed)'};
  const recent = videos.filter(v => now - Date.parse(v.publishedAt) < 30 * 86400000);
  const outliers = videos.filter(v => v.subscribers !== null && v.subscribers < smallChannelSubs && v.views > outlierMultiple * v.subscribers);
  return {
    status: 'ok',
    results: videos.length,
    medianViews: median(videos.map(v => v.views)),
    publishedLast30d: recent.length,
    outliers: outliers.map(v => ({id: v.id, title: v.title, views: v.views, subscribers: v.subscribers})),
    saturation: videos.length >= 25 && recent.length >= 10 ? 'high' : recent.length >= 5 ? 'medium' : 'low',
  };
}

// Quality-gap assessment by Gemini from result titles/descriptions.
// Optional: without a Gemini client the gap is unknown (never guessed).
export async function qualityGap(videos, geminiClient) {
  if (!Array.isArray(videos)) return {status: 'unknown', reason: 'no YouTube data'};
  if (!geminiClient) return {status: 'unknown', reason: 'no Gemini client configured'};
  const listing = videos.slice(0, 25).map((v, i) => `${i + 1}. ${v.title} (${v.publishedAt?.slice(0, 10)})`).join('\n');
  const r = await geminiClient.call({
    name: 'quality-gap', stage: 'niche-intel',
    system: 'You assess whether the top Arabic YouTube results for a topic leave a quality gap: old, weakly explained, or not simplified in Egyptian Arabic. JSON only.',
    user: 'Top results:\n' + listing + '\nReturn {"gap": 0..1, "reason": "<=120 chars Arabic"}: 1 = wide-open gap (old/weak/no simple Egyptian explanation), 0 = saturated by strong simple videos.',
    schema: {type: 'OBJECT', properties: {gap: {type: 'NUMBER'}, reason: {type: 'STRING'}}, required: ['gap', 'reason']},
  });
  if (!r.ok) return {status: 'unknown', reason: 'gemini ' + r.reason};
  const gap = Math.min(1, Math.max(0, Number(r.data.gap)));
  return {status: 'ok', gap, reason: String(r.data.reason || '')};
}
