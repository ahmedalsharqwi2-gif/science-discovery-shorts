// One-time deployment/verification. Secret values are never written into reports.
import {readFile, writeFile, unlink} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {randomBytes, createHash} from 'node:crypto';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {REPOS, OWNER, local} from './core.mjs';

const marker = 'ahmedalsharqwi2-gif-five-repositories-v1';
const required = ['CLOUDFLARE_ACCOUNT_ID', 'CLOUDFLARE_API_TOKEN', 'GITHUB_DISPATCH_TOKEN'];
const missing = required.filter(key => !process.env[key]);
if (missing.length) { console.error('Missing secure environment bindings: ' + missing.join(', ')); process.exit(2); }
const account = process.env.CLOUDFLARE_ACCOUNT_ID;
const config = JSON.parse(await readFile(new URL('./wrangler.json', import.meta.url), 'utf8'));
const deployment = randomBytes(12).toString('hex'), ops = randomBytes(32).toString('hex');
const localConfig = new URL('./wrangler.deploy.json', import.meta.url);
const report = {deployment_id: deployment, started_at: new Date().toISOString(), live: false, checks: [], generation_calls_added: 0, publication_calls_added: 0};
const reportFile = new URL('./live-verification.json', import.meta.url);
let activationAttempted = false;
let workerModified = false;
async function sourceDigest() {
  const digest = createHash('sha256');
  for (const name of ['worker.mjs','core.mjs','deploy.mjs','wrangler.json','package-lock.json']) digest.update(name + '\0').update(await readFile(new URL('./' + name, import.meta.url)));
  return digest.digest('hex');
}
const expectedSource = await sourceDigest();
report.source_sha256 = expectedSource;
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
async function cf(path, options = {}) {
  const response = await fetch('https://api.cloudflare.com/client/v4/accounts/' + account + path, {headers: {Authorization: 'Bearer ' + process.env.CLOUDFLARE_API_TOKEN}, ...options, signal: AbortSignal.timeout(30000)});
  if (response.status === 404) return null;
  if (!response.ok) throw new Error('Cloudflare API HTTP ' + response.status);
  const body = await response.json();
  if (!body.success) throw new Error('Cloudflare API did not confirm success');
  return body.result;
}
async function gh(repo, path) {
  const response = await fetch(`https://api.github.com/repos/${OWNER}/${repo}${path}`, {headers: {Authorization: 'Bearer ' + process.env.GITHUB_DISPATCH_TOKEN, Accept: 'application/vnd.github+json', 'User-Agent': 'video-factory-clock-deploy/1'}, signal: AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error('GitHub preflight HTTP ' + response.status + ': ' + repo);
  return response.json();
}
function wrangler(args, stdin) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, ['node_modules/wrangler/bin/wrangler.js', ...args, '--config', 'wrangler.deploy.json'], {cwd: new URL('.', import.meta.url), env: {...process.env, CI: 'true', WRANGLER_SEND_METRICS: 'false', XDG_CONFIG_HOME: process.env.XDG_CONFIG_HOME || join(tmpdir(), 'video-factory-wrangler-config')}, stdio: ['pipe', 'pipe', 'pipe']});
    let output = '';
    child.stdout.on('data', chunk => { output += chunk; }); child.stderr.on('data', chunk => { output += chunk; });
    child.stdin.end(stdin ? stdin + '\n' : undefined);
    child.on('error', reject);
    child.on('close', code => {
      // Deliberately omit raw CLI output: authentication diagnostics can contain secrets.
      if (code) reject(new Error('Wrangler command failed: ' + args.slice(0, 2).join(' ') + ', exit=' + code));
      else resolve(output);
    });
  });
}
async function saveConfig(probeOnly) {
  const staged = {...config, account_id: account, vars: {...config.vars, DEPLOYMENT_ID: deployment, PROBE_ONLY: String(probeOnly), DISPATCH_ENABLED: String(!probeOnly)}, triggers: {crons: probeOnly ? ['* * * * *'] : config.triggers.crons}};
  await writeFile(localConfig, JSON.stringify(staged, null, 2) + '\n');
}
async function persist() { await writeFile(reportFile, JSON.stringify(report, null, 2) + '\n'); }

try {
  const existing = await cf('/workers/scripts/' + config.name + '/settings');
  if (existing && !existing.bindings?.some(binding => binding.name === 'FACTORY_OWNER' && binding.text === marker)) throw new Error('Existing Worker does not have this project ownership marker; refusing overwrite');
  const day = local(Date.now()).day;
  if (local(Date.now()).hour >= 16) throw new Error('Too late to safely verify same-day production dry runs; no deployment performed');
  const before = {};
  for (const repo of REPOS) {
    const definition = await gh(repo, '/actions/workflows/remotion-daily.yml');
    if (definition.state !== 'active') throw new Error('Required workflow inactive: ' + repo);
    const source = await fetch(`https://raw.githubusercontent.com/${OWNER}/${repo}/main/.github/workflows/remotion-daily.yml`, {signal: AbortSignal.timeout(30000)});
    if (!source.ok) throw new Error('Public workflow definition could not be verified: ' + repo);
    const contents = await source.text();
    if (!JSON.parse(contents).on.workflow_dispatch.inputs.trigger_source) throw new Error('Independent-clock integration is not installed: ' + repo);
    before[repo] = new Set((await gh(repo, '/actions/workflows/remotion-daily.yml/runs?event=workflow_dispatch&created=' + day + '&per_page=100')).workflow_runs.map(run => run.id));
  }
  report.checks.push('Five active production workflows accept explicit independent clock/test inputs');
  await saveConfig(true);
  await wrangler(['deploy']);
  workerModified = true;
  await wrangler(['secret', 'put', 'GITHUB_DISPATCH_TOKEN'], process.env.GITHUB_DISPATCH_TOKEN);
  await wrangler(['secret', 'put', 'OPS_TOKEN'], ops);
  const subdomain = await cf('/workers/subdomain');
  if (!subdomain?.subdomain) throw new Error('Cloudflare workers.dev subdomain is unavailable; Worker remains probe-only');
  const origin = `https://${config.name}.${subdomain.subdomain}.workers.dev`;
  async function endpoint(path, method = 'GET') {
    const response = await fetch(origin + path, {method, headers: {Authorization: 'Bearer ' + ops}, signal: AbortSignal.timeout(30000)});
    if (!response.ok) throw new Error('Private Worker verification HTTP ' + response.status);
    return response.json();
  }
  let tick;
  for (let attempt = 0; attempt < 40; attempt++) {
    try { tick = await endpoint('/_ops/clock-probe'); } catch { /* DNS/cron propagation can take up to15minutes. */ }
    if (tick?.deployment_id === deployment && tick.scheduled_time) break;
    console.log('Waiting for an actual Cloudflare scheduled probe tick; production disabled');
    await pause(30000);
  }
  if (!tick?.scheduled_time || tick.deployment_id !== deployment) throw new Error('No actual Cloudflare cron tick observed; production remains disabled');
  report.clock_probe = tick; report.checks.push('An actual Cloudflare cron tick reached the Durable Object while production was disabled'); await persist();
  const dispatched = await endpoint('/_ops/test-dispatch', 'POST');
  if (!dispatched.dry_run || dispatched.results.length !== 5 || dispatched.results.some(result => result.phase !== 'dispatch_accepted' || !result.dry_run)) throw new Error('Five read-only dispatch acknowledgements were not confirmed');
  report.test_dispatches = dispatched.results; await persist();
  const verified = {};
  for (let attempt = 0; attempt < 40 && Object.keys(verified).length < 5; attempt++) {
    for (const repo of REPOS) {
      if (verified[repo]) continue;
      const rows = (await gh(repo, '/actions/workflows/remotion-daily.yml/runs?event=workflow_dispatch&created=' + day + '&per_page=100')).workflow_runs.filter(run => !before[repo].has(run.id));
      if (rows.length > 1) throw new Error('Ambiguous new test runs: ' + repo);
      const run = rows[0];
      if (!run || run.status !== 'completed') continue;
      if (run.conclusion !== 'success') throw new Error('Read-only production-controller test failed: ' + repo);
      const jobs = await gh(repo, '/actions/runs/' + run.id + '/jobs');
      let proof;
      for (const job of jobs.jobs) {
        const response = await fetch(`https://api.github.com/repos/${OWNER}/${repo}/actions/jobs/${job.id}/logs`, {headers: {Authorization: 'Bearer ' + process.env.GITHUB_DISPATCH_TOKEN}, signal: AbortSignal.timeout(30000)});
        if (!response.ok) continue;
        for (const line of (await response.text()).split('\n')) {
          const i = line.indexOf('{"run":'); if (i < 0) continue;
          try { const d = JSON.parse(line.slice(i)); if (d.trigger_source === 'cloudflare-clock-test' && d.dry_run === true && d.run === false && local(d.due_at).day === day) proof = d; } catch {}
        }
      }
      if (!proof) throw new Error('Missing exact dry-run clock provenance: ' + repo);
      verified[repo] = {run_id: run.id, url: run.html_url, decision: proof};
    }
    if (Object.keys(verified).length < 5) { console.log('Waiting for five read-only GitHub tests; production remains disabled'); await pause(30000); }
  }
  if (Object.keys(verified).length !== 5) throw new Error('Read-only integration verification timed out; production remains disabled');
  report.github_tests = verified; report.checks.push('All five actual GitHub dispatch tests completed with run=false, dry_run=true and same-day17 target'); await persist();
  if (await sourceDigest() !== expectedSource) throw new Error('Local deployment source changed after verification; refusing activation');
  activationAttempted = true;
  await saveConfig(false); await wrangler(['deploy']);
  const schedules = await cf('/workers/scripts/' + config.name + '/schedules');
  const actual = schedules?.schedules || schedules || [];
  if (!Array.isArray(actual) || JSON.stringify(actual.map(s => s.cron).sort()) !== JSON.stringify([...config.triggers.crons].sort())) throw new Error('Final cron registration does not match the intended clock');
  report.live = true; report.origin = origin; report.schedules = actual; report.completed_at = new Date().toISOString();
  report.worker_sha256 = createHash('sha256').update(await readFile(new URL('./worker.mjs', import.meta.url))).digest('hex');
  await persist(); console.log(JSON.stringify({live: true, report: 'live-verification.json', clock_probe: tick.scheduled_time, verified_repositories: Object.keys(verified), origin}));
} catch (error) {
  if (activationAttempted || workerModified) {
    try {
      const disabled = {...config, account_id: account, vars: {...config.vars, DEPLOYMENT_ID: deployment, PROBE_ONLY: 'false', DISPATCH_ENABLED: 'false'}, triggers: {crons: []}};
      await writeFile(localConfig, JSON.stringify(disabled, null, 2) + '\n');
      await wrangler(['deploy']); report.worker_left_disabled_after_failure = true;
    } catch { report.activation_state_uncertain_requires_attention = true; }
  }
  report.error = error.message; await persist(); console.error(error.message); process.exitCode = 1;
} finally { await unlink(localConfig).catch(() => {}); }
