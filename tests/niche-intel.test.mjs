import test from 'node:test';
import assert from 'node:assert/strict';
import {opportunityScore, channelFit} from '../niche_intel/score.mjs';
import {analyzeCompetition, median} from '../niche_intel/competition.mjs';
import {wikiTrend, trendsPresence} from '../niche_intel/demand.mjs';
import {passesDiversity} from '../niche_intel/bank.mjs';
import {pickTitle, titlePromiseCheck} from '../niche_intel/packaging.mjs';
import {proposeWeightChanges, MIN_SAMPLE} from '../niche_intel/feedback.mjs';
import {youtubeSearch} from '../niche_intel/sources.mjs';
import {readFileSync} from 'node:fs';
const W = JSON.parse(readFileSync(new URL('../config/selection_weights.json', import.meta.url)));

test('score: full components give deterministic 0..100 and are returned in full', () => {
  const r = opportunityScore({demand: 1, gap: 1, trend: 1, fit: 1, visual: 1, hook: 1}, W);
  assert.equal(r.score, 100); assert.equal(r.degraded, false);
  assert.deepEqual(Object.keys(r.components).sort(), ['demand', 'fit', 'gap', 'hook', 'trend', 'visual']);
});
test('score: unknown components are excluded, flagged, never guessed', () => {
  const r = opportunityScore({demand: null, gap: null, trend: 0.5, fit: 1, visual: 0.6, hook: 0.8}, W);
  assert.equal(r.degraded, true); assert.deepEqual(r.unknownComponents.sort(), ['demand', 'gap']);
});
test('score: saturation and risk penalties apply', () => {
  const base = opportunityScore({demand: 1, gap: 1, trend: 1, fit: 1, visual: 1, hook: 1}, W).score;
  assert.equal(opportunityScore({demand: 1, gap: 1, trend: 1, fit: 1, visual: 1, hook: 1, saturation: 'high', riskFlags: ['x']}, W).score, base - 35);
});
test('outliers: small channel with >10x views counted; big channel not', () => {
  const now = Date.parse('2026-11-20');
  const v = [
    {id: 'a', title: 'a', publishedAt: '2026-11-10', views: 600000, subscribers: 30000},
    {id: 'b', title: 'b', publishedAt: '2026-01-10', views: 900000, subscribers: 2000000},
    {id: 'c', title: 'c', publishedAt: '2026-11-11', views: 5000, subscribers: null}];
  const r = analyzeCompetition(v, {now});
  assert.equal(r.outliers.length, 1); assert.equal(r.outliers[0].id, 'a'); assert.equal(r.publishedLast30d, 2);
  assert.equal(median([3, 1, 2]), 2);
});
test('competition: missing YouTube data is unknown, not zero', () => {
  assert.equal(analyzeCompetition(undefined).status, 'unknown');
});
test('saturation: many recent videos => high', () => {
  const now = Date.parse('2026-11-20');
  const v = Array.from({length: 25}, (_, i) => ({id: 'v' + i, title: 't', publishedAt: '2026-11-15', views: 1000, subscribers: 100000}));
  assert.equal(analyzeCompetition(v, {now}).saturation, 'high');
});
test('wiki trend: 30d vs 90d, rising flag, short series unknown', () => {
  const now = new Date('2026-11-20');
  const mk = (d, v) => ({date: d, views: v});
  const items = [mk('20260901', 10), mk('20260915', 10), mk('20261110', 50), mk('20261115', 50)];
  const t = wikiTrend(items, {now}); assert.equal(t.status, 'ok'); assert.equal(t.rising, true);
  assert.equal(wikiTrend([], {now}).status, 'unknown');
  assert.equal(wikiTrend([mk('20261115', 5)], {now}).status, 'unknown');
});
test('trends presence: unknown when feed missing', () => {
  assert.equal(trendsPresence([], 'x').status, 'unknown');
  assert.equal(trendsPresence(['ثقب أسود جديد'], 'ثقب أسود').trending, true);
});
test('diversity: 60-day no-repeat and pillar max twice in a row', () => {
  const now = Date.parse('2026-11-20');
  const picks = [{title: 'A', pillar: 'space', date: '2026-11-19'}, {title: 'B', pillar: 'space', date: '2026-11-18'}];
  assert.equal(passesDiversity({title: 'C', pillar: 'space'}, picks, {now}).reason, 'PILLAR_THRICE_IN_A_ROW');
  assert.equal(passesDiversity({title: 'A', pillar: 'earth'}, picks, {now}).reason, 'DUPLICATE_WITHIN_60D');
  assert.equal(passesDiversity({title: 'A', pillar: 'earth'}, [{title: 'A', pillar: 'x', date: '2026-08-01'}], {now}).ok, true);
});
test('channel fit: banned topic scores 0, pillar+intent scores high, no-pillar low', () => {
  const p = JSON.parse(readFileSync(new URL('../config/niche_profile.json', import.meta.url)));
  const pil = p.pillars[0], kw = pil.keywords.find(k => k.length > 3) || pil.keywords[0];
  assert.equal(channelFit({title: p.bannedTopics[0], pillar: pil.id}, p), 0);
  assert.equal(channelFit({title: p.questionPatterns[0] + ' ' + kw, pillar: pil.id}, p), 1);
  assert.equal(channelFit({title: 'zzxxyy qqww', pillar: null}, p), 0.15);
});
test('packaging: honest title picked, repeats dropped, promise check enforced', () => {
  const t = pickTitle(['ليه الثقب الأسود مش بيبلع كل حاجة حوالينا؟', 'لن تصدق!! ثقب أسود', 'قصير'], {primaryKeyword: 'ثقب أسود', recentTitles: ['قصير']});
  assert.ok(t.includes('الثقب'));
  assert.equal(titlePromiseCheck('ليه الثقب الأسود؟', {primaryKeyword: 'الثقب الأسود', scriptSegments: ['الثقب الأسود بيشد']}).ok, true);
  assert.equal(titlePromiseCheck('ليه الثقب الأسود؟', {primaryKeyword: 'الثقب الأسود', scriptSegments: ['كلام تاني']}).ok, false);
});
test('feedback: sample under minimum makes no proposal', () => {
  const r = proposeWeightChanges(Array.from({length: MIN_SAMPLE - 1}, (_, i) => ({title: 't' + i, views: i})), [], W);
  assert.equal(r.ok, false); assert.equal(r.reason, 'sample_too_small');
});
test('feedback: shifts are bounded to 10% of the weight', () => {
  const perf = Array.from({length: 12}, (_, i) => ({title: 't' + i, views: i * 100}));
  const picks = perf.map((p, i) => ({title: p.title, components: {demand: i / 12, gap: 0.5, trend: 0.5, fit: 0.5, visual: 0.5, hook: 0.5}}));
  const r = proposeWeightChanges(perf, picks, W);
  assert.equal(r.ok, true);
  for (const [k, p] of Object.entries(r.proposal)) assert.ok(Math.abs(p.to - p.from) <= Math.ceil(W[k] * 0.1));
});
test('youtube: missing key => names the secret, no network call', async () => {
  const saved = process.env.YOUTUBE_API_KEY; delete process.env.YOUTUBE_API_KEY;
  const r = await youtubeSearch('x', {config: W, cacheDir: '/tmp/niche-test-cache'});
  if (saved) process.env.YOUTUBE_API_KEY = saved;
  assert.equal(r.status, 'missing_key'); assert.equal(r.secretName, 'YOUTUBE_API_KEY');
});
test('youtube: daily quota cap enforced', async () => {
  process.env.YOUTUBE_API_KEY = 'x-test';
  const r = await youtubeSearch('q', {config: {quota: {maxSearchCallsPerDay: 0}}, cacheDir: '/tmp/niche-test-cache2'});
  delete process.env.YOUTUBE_API_KEY;
  assert.equal(r.status, 'quota_cap_reached');
});
test('source failure: unreachable feed degrades to unknown via caller catch', async () => {
  const {newsHits} = await import('../niche_intel/sources.mjs');
  await assert.rejects(newsHits('x', {cacheDir: '/tmp/niche-test-cache3', fetcher: async () => ({ok: false, status: 503})}), /SOURCE_HTTP_503/);
});
test('youtube: budget counter increments per uncached search and caps', async () => {
  const {rmSync} = await import('node:fs'); rmSync('/tmp/niche-test-cache4', {recursive: true, force: true});
  process.env.YOUTUBE_API_KEY = 'x-test';
  const f = async () => ({ok: true, text: async () => JSON.stringify({items: []})});
  const cfg = {quota: {maxSearchCallsPerDay: 2}};
  const a = await youtubeSearch('q1', {config: cfg, cacheDir: '/tmp/niche-test-cache4', fetcher: f});
  const b = await youtubeSearch('q2', {config: cfg, cacheDir: '/tmp/niche-test-cache4', fetcher: f});
  const c = await youtubeSearch('q3', {config: cfg, cacheDir: '/tmp/niche-test-cache4', fetcher: f});
  const a2 = await youtubeSearch('q1', {config: cfg, cacheDir: '/tmp/niche-test-cache4', fetcher: f});
  delete process.env.YOUTUBE_API_KEY;
  assert.equal(a.source, 'youtube_data_api_v3'); assert.equal(b.source, 'youtube_data_api_v3');
  assert.equal(c.status, 'quota_cap_reached'); assert.equal(a2._cache, 'hit');
});
test('detectPillar: whole-word only, names with short substrings stay off-niche', async () => {
  const {detectPillar} = await import('../niche_intel/score.mjs');
  const p = JSON.parse(readFileSync(new URL('../config/niche_profile.json', import.meta.url)));
  assert.equal(detectPillar('عمر كمال', p), null);
  const pil = p.pillars[0], kw = pil.keywords.find(k => k.length > 3) || pil.keywords[0];
  assert.equal(detectPillar('خبر عن ' + kw + ' اليوم', p), pil.id);
});
