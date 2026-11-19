import {test} from 'node:test';
import assert from 'node:assert/strict';
import {fetchTrendSignals,demandScore,rerankCandidates} from '../pipeline/trend-radar.mjs';
import {chooseSources} from '../pipeline/topics.mjs';

const GT_RSS = `<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>مقبرة فرعونية</title><ht:approx_traffic>50,000+</ht:approx_traffic>
<ht:news_item><ht:news_item_title>اكتشاف أثري جديد في مصر</ht:news_item_title></ht:news_item></item>
</channel></rss>`;
const AUTOCOMPLETE = '["تاريخ",[["تاريخ مصر القديم"],["تاريخ الفراعنة"]]]';
const YT_FEED = `<?xml version="1.0"?><feed xmlns:media="http://search.yahoo.com/mrss/" xmlns:yt="http://www.youtube.com/xml/schemas/2015">
<entry><title>أسرار الحضارة الفرعونية</title><published>2026-11-17T00:00:00Z</published>
<media:group><media:community><media:statistics views="2000000"/></media:community></media:group></entry>
</feed>`;

function fakeFetcher(map) {
  return async (url) => {
    for (const [needle, body] of Object.entries(map)) {
      if (url.includes(needle)) return new Response(body, {status: 200, headers: {'content-type': 'application/xml'}});
    }
    throw Error('FEED_HTTP_404');
  };
}
const fetcher = fakeFetcher({
  'trends.google.com': GT_RSS,
  'suggestqueries.google.com': AUTOCOMPLETE,
  'feeds/videos.xml': YT_FEED,
  'api.wikimedia.org': '{"events":[{"text":"افتتاح متحف الحضارة","year":2017}],"birthdays":[],"deaths":[]}',
});
const config = {
  enabled: true, mode: 'rerank',
  googleTrends: {geo: 'EG'},
  autocompleteSeeds: ['تاريخ'],
  competitorChannelIds: ['UCfake'],
  onThisDay: {enabled: true, lang: 'ar'},
  weights: {demand: 1.0, recency: 0.5},
  excludedTerms: [],
};

test('fetchTrendSignals parses trends, suggestions, competitor views and on-this-day', async () => {
  const now = Date.parse('2026-11-19T00:00:00Z');
  const {signals, diagnostics, degraded} = await fetchTrendSignals(config, {fetcher, now});
  assert.equal(degraded, false);
  assert.equal(signals.trends[0].term, 'مقبرة فرعونية');
  assert.deepEqual(signals.suggestions.map(s => s.text), ['تاريخ مصر القديم', 'تاريخ الفراعنة']);
  assert.equal(signals.competitorVideos[0].viewsPerDay, 1000000);
  assert.equal(signals.onThisDay[0].text, 'افتتاح متحف الحضارة');
  assert.ok(diagnostics.every(d => d.status === 'ok'));
});

test('fetchTrendSignals degrades to empty signals when every source fails', async () => {
  const failing = async () => { throw Error('FEED_HTTP_503'); };
  const {signals, degraded} = await fetchTrendSignals(config, {fetcher: failing});
  assert.equal(degraded, true);
  assert.ok(Object.values(signals).every(list => list.length === 0));
});

test('demandScore matches trend terms against candidate text', () => {
  const signals = {trends: [{term: 'مقبرة فرعونية', news: []}], suggestions: [], competitorVideos: [], onThisDay: [], hackerNews: [], reddit: []};
  const hit = demandScore('اكتشاف مقبرة فرعونية جديدة', signals, config);
  assert.ok(hit.demand > 0 && hit.matches.some(m => m.kind === 'google_trend'));
  const miss = demandScore('نتيجة مباراة كرة قدم', signals, config);
  assert.equal(miss.demand, 0);
});

test('rerankCandidates lifts in-demand topics above fresher ones', () => {
  const now = Date.parse('2026-11-19T00:00:00Z');
  const mk = (id, title, published, official = false) => ({source: {id, title, text: '', published, official}});
  const older = mk('a', 'اكتشاف مقبرة فرعونية جديدة', '2026-11-16T00:00:00Z');
  const fresher = mk('b', 'خبر رياضي عاجل', '2026-11-18T23:00:00Z', true);
  const signals = {trends: [{term: 'مقبرة فرعونية', news: []}], suggestions: [], competitorVideos: [], onThisDay: [], hackerNews: [], reddit: []};
  const {candidates, decisions} = rerankCandidates([fresher, older], signals, config, {now});
  assert.equal(candidates[0].source.id, 'a');
  assert.ok(decisions.find(d => d.id === 'a').score > decisions.find(d => d.id === 'b').score);
});

test('excluded terms hard-drop a candidate to the bottom', () => {
  const cfg = {...config, excludedTerms: ['رياضي']};
  const mk = (id, title) => ({source: {id, title, text: '', published: '2026-11-18T00:00:00Z', official: false}});
  const {candidates, decisions} = rerankCandidates([mk('x', 'خبر رياضي'), mk('y', 'قصة تاريخية')], {trends: [], suggestions: [], competitorVideos: [], onThisDay: [], hackerNews: [], reddit: []}, cfg, {now: Date.parse('2026-11-19T00:00:00Z')});
  assert.equal(candidates[0].source.id, 'y');
  assert.equal(decisions.find(d => d.id === 'x').excluded, true);
});

test('chooseSources keeps legacy behavior when trend signals are absent', () => {
  const mk = (id, published) => ({id, title: 'خبر ' + id, url: 'https://example.com/' + id, text: 'نص', published, official: true, publisher: 'example.com', primaryRefs: []});
  const sources = [mk('old', '2026-11-17T00:00:00Z'), mk('new', '2026-11-18T00:00:00Z')];
  const cfg = {maxAgeHours: 96, channelRelevance: {enabled: false}};
  const chosen = chooseSources(sources, cfg, {now: Date.parse('2026-11-19T00:00:00Z')});
  assert.equal(chosen.selected.id, 'new');
  assert.deepEqual(chosen.trend, []);
});

test('everydayBoost lifts concrete everyday topics', () => {
  const signals = {trends: [], suggestions: [], competitorVideos: [], onThisDay: [], hackerNews: [], reddit: []};
  const cfg = {everydayTerms: ['غسالة', 'مطبخ'], everydayBoost: 1.5};
  const hit = demandScore('الغسالة بتغسل إزاي', signals, cfg);
  assert.equal(hit.demand, 1.5);
  assert.deepEqual(hit.matches, [{kind: 'everyday_curiosity', label: 'غسالة', weight: 1.5}]);
  const miss = demandScore('نظرية الأوتار الفائقة', signals, cfg);
  assert.equal(miss.demand, 0);
});
