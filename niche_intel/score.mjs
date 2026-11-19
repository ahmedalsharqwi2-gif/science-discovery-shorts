// niche_intel/score.mjs - Opportunity Score 0..100. Weights live in
// config/selection_weights.json, not in code. Components are returned in
// full so state/niche/<date>.json stays auditable. Unknown components score
// null and are EXCLUDED from the total, which is then rescaled over the
// known components and flagged degraded - a missing source never becomes a
// fake number (owner rules 1 and 3).
const DEFAULT_WEIGHTS = {demand: 30, gap: 25, trend: 10, fit: 15, visual: 10, hook: 10, penalties: {saturationHigh: -15, saturationMedium: -5, risk: -20}};

export function opportunityScore({demand, gap, trend, fit, visual, hook, saturation, riskFlags = []}, weights = DEFAULT_WEIGHTS) {
  const w = {...DEFAULT_WEIGHTS, ...weights, penalties: {...DEFAULT_WEIGHTS.penalties, ...(weights.penalties || {})}};
  const parts = {demand, gap, trend, fit, visual, hook};
  const known = Object.entries(parts).filter(([, v]) => Number.isFinite(v) && v >= 0 && v <= 1);
  const unknown = Object.keys(parts).filter(k => !known.some(([n]) => n === k));
  const weightSum = known.reduce((s, [k]) => s + w[k], 0);
  const rawKnown = known.reduce((s, [k, v]) => s + v * w[k], 0);
  let score = weightSum > 0 ? rawKnown / weightSum * 100 : 0;
  const penalty = (saturation === 'high' ? w.penalties.saturationHigh : saturation === 'medium' ? w.penalties.saturationMedium : 0) + (riskFlags.length ? w.penalties.risk : 0);
  score = Math.round(Math.min(100, Math.max(0, score + penalty)));
  return {score, degraded: unknown.length > 0, unknownComponents: unknown, components: Object.fromEntries(known), penalties: {saturation, riskFlags, applied: penalty}, weights: w};
}

// Channel fit: pillar match + search-intent match from niche_profile.json.
export function channelFit(candidate, profile) {
  if (!profile?.pillars?.length) return null;
  if (!candidate.pillar) candidate = {...candidate, pillar: detectPillar(candidate.title, profile)};
  const pillarHit = candidate.pillar && profile.pillars.some(p => p.id === candidate.pillar || p.title === candidate.pillar);
  const intentHit = profile.questionPatterns?.some(q => candidate.title?.includes(q.replace('…', '').trim()));
  const banned = profile.bannedTopics?.some(b => candidate.title?.includes(b));
  if (banned) return 0;
  if (!pillarHit) return 0.15; // no pillar match: weak fit, off-niche gate in run.mjs decides
  let s = 0.4; // in-niche baseline
  if (pillarHit) s += 0.4;
  if (intentHit) s += 0.2;
  return Math.min(1, s);
}

// Keyword-based pillar detection for candidates with no pillar (e.g. raw
// trending titles). Null = off-niche. Gemini classification can refine this in CI.
export function detectPillar(title, profile) {
  const t = (title || '').toLowerCase();
  for (const p of profile.pillars || []) if ((p.keywords || []).some(k => hasWord(t, k.toLowerCase()))) return p.id;
  return null;
}

// Whole-word match (optionally with the Arabic definite article), so short
// keywords never match inside unrelated words or names.
function hasWord(text, kw) {
  const padded = ' ' + text.replace(/[^\p{L}\p{N} ]/gu, ' ') + ' ';
  return padded.includes(' ' + kw + ' ') || padded.includes(' ال' + kw + ' ');
}
