// niche_intel/sources.mjs - demand-signal fetchers.
// Rules (owner spec 2026-11-20): official APIs or open RSS only, clear
// User-Agent, caching, rate limits, no protected-page scraping. Every number
// carries its source and fetch date; unavailable data is recorded as
// `unknown`, never estimated. YouTube Data API v3 is OPTIONAL: without
// YOUTUBE_API_KEY the tool runs degraded on free sources and says so.
import {createHash} from 'node:crypto';
import {mkdir, readFile, writeFile, rename} from 'node:fs/promises';
import path from 'node:path';

const hash = s => createHash('sha256').update(s).digest('hex');
const UA = 'NicheIntel/1.0 (+https://github.com/ahmedalsharqwi2-gif/science-discovery-shorts; topic research; cached)';
const YOUTUBE_KEY_NAME = 'YOUTUBE_API_KEY'; // repo secret name; value never printed

async function cached(cacheDir, key, ttlMs, produce, {clock = Date.now} = {}) {
  const file = path.join(cacheDir, hash(key) + '.json');
  try {
    const row = JSON.parse(await readFile(file, 'utf8'));
    if (row.key === key && row.expiresAt > clock()) return {...row.data, _cache: 'hit'};
  } catch (e) { if (e.code !== 'ENOENT' && !(e instanceof SyntaxError)) throw e; }
  const data = await produce();
  await mkdir(cacheDir, {recursive: true});
  const tmp = file + '.' + process.pid + '.tmp';
  await writeFile(tmp, JSON.stringify({key, fetchedAt: new Date(clock()).toISOString(), expiresAt: clock() + ttlMs, data}));
  await rename(tmp, file);
  return {...data, _cache: 'miss'};
}

async function getText(url, {fetcher = fetch, timeout = 20000} = {}) {
  const res = await fetcher(url, {redirect: 'follow', signal: AbortSignal.timeout(timeout), headers: {'User-Agent': UA, Accept: 'application/rss+xml, application/xml, application/json, text/xml;q=0.9'}});
  if (!res.ok) throw Error('SOURCE_HTTP_' + res.status);
  return res.text();
}

// Minimal RSS/Atom item extractor (no dependency): title + link per item.
const tag = (x, t) => { const m = x.match(new RegExp('<' + t + '(?:\\s[^>]*)?>([\\s\\S]*?)</' + t + '>')); return m ? m[1].replace(/<!\\[CDATA\\[|\\]\\]>/g, '').trim() : ''; };
const xmlItems = xml => {
  const items = xml.match(/<(item|entry)(\s[^>]*)?>[\s\S]*?<\/\1>/g) || [];
  return items.map(x => ({title: tag(x, 'title'), link: x.match(/<link[^>]*href="([^"]+)"/)?.[1] || tag(x, 'link') || tag(x, 'guid')})).filter(i => i.title);
};

// Google Trends daily trending searches, Egypt (official public RSS).
export async function trendsEg(opts = {}) {
  return cached(opts.cacheDir || '.cache/niche', 'trends-rss-eg', 6 * 3600000, async () => {
    const items = xmlItems(await getText('https://trends.google.com/trending/rss?geo=EG', opts));
    return {source: 'google_trends_rss_eg', fetchedAt: new Date().toISOString(), items: items.map(i => i.title).filter(Boolean).slice(0, 50)};
  }, opts);
}

// Arabic Wikipedia pageviews for one article, last `days` days.
// Returns daily series; caller computes 30v90 comparisons. unknown on miss.
export async function wikiPageviews(article, {days = 90, ...opts} = {}) {
  const end = new Date(), start = new Date(Date.now() - days * 86400000);
  const fmt = d => d.toISOString().slice(0, 10).replace(/-/g, '');
  const key = 'wiki:' + article + ':' + fmt(start) + ':' + fmt(end);
  return cached(opts.cacheDir || '.cache/niche', key, 7 * 86400000, async () => {
    const url = 'https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/ar.wikipedia/all-access/all-agents/' + encodeURIComponent(article.replace(/ /g, '_')) + '/daily/' + fmt(start) + '00/' + fmt(end) + '00';
    const raw = await getText(url, opts);
    const items = (JSON.parse(raw).items || []).map(r => ({date: r.timestamp.slice(0, 8), views: r.views}));
    return {source: 'wikimedia_pageviews_ar', article, fetchedAt: new Date().toISOString(), items};
  }, opts);
}

// Google News RSS search hits (Arabic, Egypt edition) - secondary interest signal.
export async function newsHits(query, opts = {}) {
  return cached(opts.cacheDir || '.cache/niche', 'news:' + query, 12 * 3600000, async () => {
    const items = xmlItems(await getText('https://news.google.com/rss/search?q=' + encodeURIComponent(query) + '&hl=ar&gl=EG&ceid=EG:ar', opts));
    return {source: 'google_news_rss_ar_eg', query, fetchedAt: new Date().toISOString(), count: items.length, headlines: items.slice(0, 10).map(i => i.title)};
  }, opts);
}

// Reddit public search RSS - secondary interest signal. Optional per spec.
export async function redditHits(query, opts = {}) {
  if (opts.enabled === false) return {source: 'reddit_rss', query, status: 'disabled_by_config'};
  return cached(opts.cacheDir || '.cache/niche', 'reddit:' + query, 12 * 3600000, async () => {
    const items = xmlItems(await getText('https://www.reddit.com/search.rss?q=' + encodeURIComponent(query), opts));
    return {source: 'reddit_search_rss', query, fetchedAt: new Date().toISOString(), count: items.length};
  }, opts);
}

// YouTube Data API v3 (OFFICIAL, needs YOUTUBE_API_KEY repo secret).
// search.list costs 100 quota units of a ~10,000/day default budget, so the
// daily query cap lives in config and every call is cached for a week.
// Without the key: returns status missing_key and the name of the secret.
export async function youtubeSearch(query, {config = {}, ...opts} = {}) {
  const key = process.env[YOUTUBE_KEY_NAME];
  if (!key) return {status: 'missing_key', secretName: YOUTUBE_KEY_NAME, note: 'YouTube demand/competition metrics unknown; free sources only'};
  const maxPerDay = config.quota?.maxSearchCallsPerDay ?? 20;
  const dir = opts.cacheDir || '.cache/niche';
  const budgetFile = path.join(dir, 'yt-budget-' + new Date().toISOString().slice(0, 10) + '.json');
  const used = await readFile(budgetFile, 'utf8').then(t => JSON.parse(t).used || 0, () => 0);
  const cacheFile = path.join(dir, hash('yt:' + query) + '.json');
  const willHitCache = await readFile(cacheFile, 'utf8').then(t => JSON.parse(t).expiresAt > Date.now(), () => false);
  if (!willHitCache && used >= maxPerDay) return {status: 'quota_cap_reached', maxPerDay, note: 'daily search.list cap from config/selection_weights.json quota'};
  if (!willHitCache) { await mkdir(dir, {recursive: true}); await writeFile(budgetFile, JSON.stringify({used: used + 1})); }
  return cached(opts.cacheDir || '.cache/niche', 'yt:' + query, 7 * 86400000, async () => {
    const search = await getText('https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&maxResults=25&regionCode=EG&relevanceLanguage=ar&q=' + encodeURIComponent(query), opts).then(JSON.parse);
    const ids = (search.items || []).map(i => i.id.videoId).filter(Boolean);
    let videos = [];
    if (ids.length) {
      const stats = await getText('https://www.googleapis.com/youtube/v3/videos?part=statistics,snippet&id=' + ids.join(','), opts).then(JSON.parse);
      const chanIds = [...new Set((stats.items || []).map(v => v.snippet.channelId))];
      let channels = {};
      if (chanIds.length) {
        const ch = await getText('https://www.googleapis.com/youtube/v3/channels?part=statistics&id=' + chanIds.join(','), opts).then(JSON.parse);
        channels = Object.fromEntries((ch.items || []).map(c => [c.id, Number(c.statistics.subscriberCount) || 0]));
      }
      videos = (stats.items || []).map(v => ({id: v.id, title: v.snippet.title, publishedAt: v.snippet.publishedAt, views: Number(v.statistics.viewCount) || 0, subscribers: channels[v.snippet.channelId] ?? null}));
    }
    return {source: 'youtube_data_api_v3', query, fetchedAt: new Date().toISOString(), videos};
  }, opts);
}

export const SOURCE_REGISTRY = [
  {id: 'google_trends_rss_eg', kind: 'official_public_rss', defaultEnabled: true},
  {id: 'wikimedia_pageviews_ar', kind: 'official_api_no_key', defaultEnabled: true},
  {id: 'google_news_rss_ar_eg', kind: 'public_rss', defaultEnabled: true},
  {id: 'reddit_search_rss', kind: 'public_rss_unofficial', defaultEnabled: false, note: 'optional, off by default per owner rule 4'},
  {id: 'youtube_data_api_v3', kind: 'official_api_key', secretName: YOUTUBE_KEY_NAME, defaultEnabled: 'when key present'},
];
