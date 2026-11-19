// niche_intel/demand.mjs - demand signals per candidate topic.
// Every figure carries source + fetch date; unavailable stays `unknown`.
import {wikiPageviews, newsHits, redditHits, youtubeSearch, trendsEg} from './sources.mjs';

// Normalize a 30-day vs 90-day Wikipedia pageview trend to 0..1.
// Both windows come from the same fetched series. Avg of 0 views is real data
// (nobody searched it), not unknown.
export function wikiTrend(items, {now = new Date()} = {}) {
  if (!items?.length) return {status: 'unknown', reason: 'no pageview data (missing article or fetch failed)'};
  const cutoff = new Date(now.getTime() - 30 * 86400000);
  const day = d => new Date(d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6, 8));
  const recent = items.filter(i => day(i.date) >= cutoff), older = items.filter(i => day(i.date) < cutoff);
  const avg = a => a.length ? a.reduce((s, i) => s + i.views, 0) / a.length : null;
  const r = avg(recent), o = avg(older);
  if (r === null || o === null) return {status: 'unknown', reason: 'series shorter than 30 days'};
  return {status: 'ok', avg30: Math.round(r), avg90: Math.round(o), rising: r > o, ratio: o > 0 ? +(r / o).toFixed(3) : (r > 0 ? Infinity : 1)};
}

// Presence among current Egyptian trending searches (exact/loose title match).
export function trendsPresence(trendTitles, keyword) {
  if (!trendTitles?.length) return {status: 'unknown', reason: 'trends RSS unavailable'};
  const k = keyword.trim();
  const hit = trendTitles.find(t => t.includes(k) || k.includes(t));
  return {status: 'ok', trending: Boolean(hit), matched: hit || null};
}

// Demand 0..30 composite. Missing components contribute unknown, not guesses.
export async function demandSignal(candidate, {config, ...opts}) {
  const kw = candidate.primaryKeyword;
  const [wiki, news, reddit, yt] = await Promise.all([
    candidate.wikiArticle ? wikiPageviews(candidate.wikiArticle, opts).then(w => wikiTrend(w.items, opts)).catch(() => ({status: 'unknown', reason: 'pageviews fetch failed'})) : {status: 'unknown', reason: 'no wikiArticle mapped'},
    newsHits(kw, opts).catch(() => ({source: 'google_news_rss_ar_eg', status: 'unknown', reason: 'fetch failed'})),
    redditHits(kw, {enabled: config.sources?.reddit === true, ...opts}).catch(() => ({status: 'unknown', reason: 'fetch failed'})),
    youtubeSearch(kw, {config, ...opts}).catch(() => ({status: 'unknown', reason: 'fetch failed'})),
  ]);
  return {keyword: kw, wiki, news, reddit, youtube: yt.status ? {status: yt.status, secretName: yt.secretName, note: yt.note} : yt};
}

export async function trendingCandidates(opts = {}) {
  const t = await trendsEg(opts).catch(() => null);
  return t ? t.items.map(title => ({title, source: 'google_trends_rss_eg', fetchedAt: t.fetchedAt, kind: 'trending'})) : [];
}
