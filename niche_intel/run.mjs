// niche_intel/run.mjs - daily niche research orchestrator.
// Merges trending candidates with bank ideas at the configured ratio, scores
// each, records a fully auditable justification in state/niche/<date>.json,
// and writes packaging.json for the winner. Publishes nothing.
//   node niche_intel/run.mjs research [--offline-fixtures tests/fixtures/niche]
//   node niche_intel/run.mjs bank-seed          (needs GEMINI_API_KEY)
//   node niche_intel/run.mjs feedback           (weekly; writes proposal PR body)
import {mkdir, readFile, writeFile, readdir} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {demandSignal, trendingCandidates} from './demand.mjs';
import {analyzeCompetition, qualityGap} from './competition.mjs';
import {opportunityScore, channelFit, detectPillar} from './score.mjs';
import {loadBank, saveBank, generateIdeas, passesDiversity} from './bank.mjs';
import {generatePackaging} from './packaging.mjs';
import {loadPerformanceCsv, proposeWeightChanges, weeklyInsightsMd} from './feedback.mjs';
import {youtubeSearch} from './sources.mjs';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const readJson = async p => JSON.parse(await readFile(path.join(root, p), 'utf8'));

import {nicheGemini} from './gemini-adapter.mjs';
const gemini = nicheGemini;

async function recentPicks(stateDir = 'state/niche') {
  let files = [];
  try { files = (await readdir(path.join(root, stateDir))).filter(f => f.endsWith('.json')).sort().reverse(); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  const picks = [];
  for (const f of files.slice(0, 90)) {
    const j = JSON.parse(await readFile(path.join(root, stateDir, f), 'utf8'));
    if (j.selected) picks.push({title: j.selected.title, pillar: j.selected.pillar, date: j.date, components: j.selected.score?.components});
  }
  return picks;
}

export async function research({offlineFixtures = null, out = process.stdout} = {}) {
  const profile = await readJson('config/niche_profile.json');
  const weights = await readJson('config/selection_weights.json');
  const cacheDir = path.join(root, '.cache/niche');
  const opts = offlineFixtures ? {cacheDir: offlineFixtures} : {cacheDir};

  const [trending, bank, picks] = await Promise.all([trendingCandidates(opts), loadBank(path.join(root, 'topic_bank')), recentPicks()]);
  const ratio = weights.bankMix || {evergreen: 70, trending: 30};
  const bankPool = bank.filter(i => i.status === 'validated');
  const pendingPool = bank.filter(i => i.status === 'pending');
  const candidates = [...trending.map(t => ({...t, primaryKeyword: t.title, pillar: detectPillar(t.title, profile)})), ...(bankPool.length ? bankPool : pendingPool).map(b => ({...b, kind: b.kind || 'evergreen'}))];
  const warnings = [];
  if (!bankPool.length && pendingPool.length) warnings.push('no validated bank ideas; pending ideas used and flagged');

  const g = await gvar();
  const scored = [];
  for (const c of candidates.slice(0, weights.maxCandidatesPerRun || 40)) {
    if (!c.pillar) { scored.push({candidate: c, eligible: false, reason: 'OFF_NICHE'}); continue; }
    const div = passesDiversity(c, picks);
    if (!div.ok) { scored.push({candidate: c, eligible: false, reason: div.reason}); continue; }
    const demand = await demandSignal(c, {config: weights, ...opts});
    const yt = demand.youtube?.videos ? demand.youtube : (demand.youtube?.status === 'missing_key' ? null : await youtubeSearch(c.primaryKeyword, {config: weights, ...opts}).catch(() => null));
    const comp = yt?.videos ? analyzeCompetition(yt.videos) : {status: 'unknown', reason: demand.youtube?.note || 'YouTube unavailable'};
    const gap = yt?.videos ? await qualityGap(yt.videos, g) : {status: 'unknown', reason: 'no YouTube results'};
    const score = opportunityScore({
      demand: demand.wiki.status === 'ok' ? Math.min(1, demand.wiki.avg30 / 5000) : (demand.news?.count != null ? Math.min(1, demand.news.count / 30) : null),
      gap: gap.status === 'ok' ? gap.gap : (comp.status === 'ok' ? Math.min(1, comp.outliers.length / 3) : null),
      trend: demand.wiki.status === 'ok' ? (demand.wiki.rising ? Math.min(1, (demand.wiki.ratio - 1)) : 0.1) : (demand.youtube?.trending || c.kind === 'trending' ? 0.5 : null),
      fit: channelFit(c, profile),
      visual: profile.visualFilmabilityDefault ?? 0.6,
      hook: /؟|ليه|إزاي|إيه|ماذا|حقيقة|لغز|قصة/.test(c.title) ? 0.8 : 0.4,
      saturation: comp.saturation,
      riskFlags: (profile.bannedTopics || []).filter(b => c.title?.includes(b)),
    }, weights);
    scored.push({candidate: c, eligible: true, demand, competition: comp, qualityGap: gap, score});
  }

  const ranked = scored.filter(s => s.eligible).sort((a, b) => b.score.score - a.score.score);
  const trendingCut = Math.ceil((weights.maxCandidatesPerRun || 40) * (ratio.trending / 100));
  const selected = ranked[0] || null;
  const date = new Date().toISOString().slice(0, 10);
  const justification = {
    date, channel: profile.channel,
    selected: selected ? {title: selected.candidate.title, pillar: selected.candidate.pillar, kind: selected.candidate.kind || 'trending', status: selected.candidate.status || 'trending-signal', score: selected.score} : null,
    rankedTop10: ranked.slice(0, 10).map(s => ({title: s.candidate.title, score: s.score.score, degraded: s.score.degraded, sources: [s.demand.wiki.status === 'ok' ? 'wikimedia' : null, s.demand.news?.count != null ? 'google_news' : null, s.competition.status === 'ok' ? 'youtube_data_api' : null].filter(Boolean)})),
    warnings: [...warnings, ...(scored.some(s => s.reason === 'OFF_NICHE') ? [scored.filter(s => s.reason === 'OFF_NICHE').length + ' trending candidates dropped as off-niche (no pillar match)'] : [])], offNicheDropped: scored.filter(s => s.reason === 'OFF_NICHE').map(s => s.candidate.title), trendingMixTarget: ratio, trendingCandidatesSeen: trending.length,
    secrets: {YOUTUBE_API_KEY: process.env.YOUTUBE_API_KEY ? 'present' : 'MISSING - degraded to free sources', GEMINI_API_KEY: process.env.GEMINI_API_KEY ? 'present' : 'MISSING - packaging/quality-gap/bank-seed skipped'},
  };
  await mkdir(path.join(root, 'state/niche'), {recursive: true});
  await writeFile(path.join(root, 'state/niche', date + '.json'), JSON.stringify(justification, null, 2) + '\n');

  let packaging = {ok: false, reason: 'no_selection'};
  if (selected && g) {
    packaging = await generatePackaging(selected.candidate, profile, g);
    if (packaging.ok) await writeFile(path.join(root, 'state/niche', date + '.packaging.json'), JSON.stringify(packaging.packaging, null, 2) + '\n');
  } else if (selected && !g) packaging = {ok: false, reason: 'no_gemini', note: 'packaging.json generated in CI where GEMINI_API_KEY exists'};
  out.write(JSON.stringify({date, selected: justification.selected, warnings, secrets: justification.secrets, packaging: packaging.ok ? 'written' : packaging.reason, candidates: ranked.length}) + '\n');
  return justification;
}

async function gvar() { return gemini(); }

async function bankSeed() {
  const profile = await readJson('config/niche_profile.json');
  const g = await gemini();
  const existing = await loadBank(path.join(root, 'topic_bank'));
  const r = await generateIdeas(profile, existing, g, {target: 150});
  if (!r.ok) { console.log(JSON.stringify(r)); process.exitCode = 1; return; }
  await saveBank(path.join(root, 'topic_bank'), [...existing, ...r.ideas]);
  console.log(JSON.stringify({added: r.ideas.length, total: existing.length + r.ideas.length, status: 'pending'}));
}

async function feedback() {
  const weights = await readJson('config/selection_weights.json');
  const perf = await loadPerformanceCsv(path.join(root, 'feedback/inbox'));
  const picks = await recentPicks();
  const result = proposeWeightChanges(perf, picks, weights);
  const md = weeklyInsightsMd(result);
  await writeFile(path.join(root, 'docs/WEEKLY_INSIGHTS.md'), md);
  console.log(JSON.stringify(result.ok ? {proposal: result.proposal, sample: result.sample} : result));
}

const cmd = process.argv[2];
if (cmd === 'research') await research({offlineFixtures: process.argv.includes('--offline-fixtures') ? process.argv[process.argv.indexOf('--offline-fixtures') + 1] : null});
else if (cmd === 'bank-seed') await bankSeed();
else if (cmd === 'feedback') await feedback();
else { console.error('usage: run.mjs research|bank-seed|feedback'); process.exitCode = 2; }
