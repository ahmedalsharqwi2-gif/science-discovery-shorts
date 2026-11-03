// Only starts existing GitHub workflows. No Gemini, Buffer or publication keys.
export const OWNER = 'ahmedalsharqwi2-gif';
export const REPOS = Object.freeze(['science-discovery-shorts', 'arabic-horror-stories', 'documented-history-stories', 'ai-news-daily', 'stickman-what-if-shorts']);
const ZONE = 'Africa/Cairo';
const formatter = new Intl.DateTimeFormat('en-CA', {timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23'});
export function local(value) {
  const date = new Date(value);
  if (!Number.isFinite(+date)) throw new Error('Invalid clock timestamp');
  const p = Object.fromEntries(formatter.formatToParts(date).map(x => [x.type, x.value]));
  return {day: `${p.year}-${p.month}-${p.day}`, hour: +p.hour, minute: +p.minute};
}
export function clockOperation(scheduled, now) {
  const s = local(scheduled), n = local(now);
  if (s.day !== n.day) return null; // Never move a missed trigger into another day.
  if (s.hour === 9 && [0, 17].includes(s.minute) && n.hour === 9) return {kind: 'production', day: s.day};
  if (s.hour === 17 && s.minute === 35 && n.hour >= 17 && n.hour < 20) return {kind: 'publication-audit', day: s.day};
  return null;
}
function workflow(kind) { return kind === 'publication-audit' ? 'remotion-health.yml' : 'remotion-daily.yml'; }
function headers(env) {
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error('GitHub dispatch credential is not configured');
  return {'Authorization': `Bearer ${env.GITHUB_DISPATCH_TOKEN}`, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'video-factory-independent-clock/1', 'Content-Type': 'application/json'};
}
async function api(env, path, method = 'GET', payload, http = fetch, raw = false) {
  const response = await http('https://api.github.com' + path, {method, headers: headers(env), ...(payload ? {body: JSON.stringify(payload)} : {}), signal: AbortSignal.timeout(30000)});
  if (!response.ok) { const error = new Error('GitHub HTTP ' + response.status); error.httpStatus = response.status; throw error; }
  return response.status === 204 ? null : raw ? response.text() : response.json();
}
async function recordedDecision(env, repo, run, http) {
  const root = `/repos/${OWNER}/${repo}/actions`;
  const data = await api(env, `${root}/runs/${run.id}/jobs`, 'GET', undefined, http);
  for (const job of data.jobs || []) {
    const logs = await api(env, `${root}/jobs/${job.id}/logs`, 'GET', undefined, http, true);
    for (const line of logs.split('\n')) {
      const start = line.indexOf('{"run":'); if (start < 0) continue;
      try { return JSON.parse(line.slice(start)); } catch { /* A malformed log line proves nothing. */ }
    }
  }
  return null;
}
export async function dispatchOnce(store, env, input, http = fetch, now = Date.now()) {
  if (!REPOS.includes(input.repo) || !['production', 'publication-audit', 'test'].includes(input.kind)) throw new Error('Unapproved operation/repository');
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error('GitHub dispatch credential is not configured');
  const today = local(now);
  if (input.day !== today.day) throw new Error('Cross-day dispatch refused');
  if (input.kind === 'production' && today.hour !== 9) throw new Error('Production dispatch outside the Cairo9 window');
  if (input.kind === 'test' && today.hour >= 16) throw new Error('Late dry-run test refused');
  const prior = await store.get('receipt');
  if (prior) return {...prior, reused: true};
  const root = `/repos/${OWNER}/${input.repo}/actions/workflows/${workflow(input.kind)}`;
  if (input.kind !== 'test') {
    const found = [];
    for (let page = 1; page <= 5; page++) {
      const data = await api(env, `${root}/runs?created=${input.day}&per_page=100&page=${page}`, 'GET', undefined, http);
      if (!Array.isArray(data.workflow_runs)) throw new Error('Invalid GitHub run inventory');
      found.push(...data.workflow_runs);
      if (data.workflow_runs.length < 100) break;
      if (page === 5) throw new Error('Incomplete run inventory; no dispatch');
    }
    const candidates = found.filter(r => {
      const p = local(r.created_at);
      return p.day === input.day && (input.kind === 'production' ? p.hour >= 9 : p.hour >= 17 && ['queued', 'in_progress', 'waiting', 'pending', 'requested'].includes(r.status));
    });
    for (const existing of candidates) {
      if (['queued','in_progress','waiting','pending','requested'].includes(existing.status)) {
        const observation = {phase: 'existing_run_in_progress_preserved', run_id: existing.id, run_status: existing.status, repo: input.repo, day: input.day};
        await store.put('observation', observation); // Backup may inspect its final result; no new dispatch now.
        return observation;
      }
      const decision = await recordedDecision(env, input.repo, existing, http);
      // A delayed opposite-DST no-op or an explicit dry test must not suppress real production.
      if (decision?.reason === 'other DST trigger' || decision?.dry_run === true) continue;
      let correctTarget = false;
      try { const p = local(decision?.due_at); correctTarget = p.day === input.day && p.hour === 17 && p.minute === 0 && new Date(decision.due_at).getUTCSeconds() === 0; } catch {}
      const valid = existing.conclusion === 'success' && correctTarget && decision?.dry_run === false;
      const receipt = {phase: valid ? 'existing_run_preserved' : 'existing_run_needs_attention', run_id: existing.id, run_status: existing.status, run_conclusion: existing.conclusion, repo: input.repo, day: input.day};
      await store.transaction(async tx => { if (!(await tx.get('receipt'))) await tx.put('receipt', receipt); });
      return receipt;
    }
  }
  const claimed = await store.transaction(async tx => {
    if (await tx.get('receipt')) return false;
    await tx.put('receipt', {phase: 'intent', repo: input.repo, day: input.day, kind: input.kind, created_at: new Date(now).toISOString()});
    return true;
  });
  if (!claimed) return {...await store.get('receipt'), reused: true};
  const inputs = input.kind === 'publication-audit'
    ? {date: input.day, phase: 'postpublish'}
    : {publish_date: input.day, dry_run: input.kind === 'test', trigger_source: input.kind === 'test' ? 'cloudflare-clock-test' : 'cloudflare-clock'};
  try {
    await api(env, root + '/dispatches', 'POST', {ref: 'main', inputs}, http);
    const receipt = {phase: 'dispatch_accepted', repo: input.repo, day: input.day, kind: input.kind, workflow: workflow(input.kind), dry_run: input.kind === 'test', accepted_at: new Date(now).toISOString(), production_completion_claimed: false};
    await store.put('receipt', receipt);
    return receipt;
  } catch (error) {
    // The request may already have reached GitHub. Retain intent; never send twice.
    const receipt = {phase: error.httpStatus ? 'dispatch_rejected' : 'dispatch_uncertain', repo: input.repo, day: input.day, kind: input.kind, ...(error.httpStatus ? {http_status: error.httpStatus} : {}), automatic_retry: false};
    await store.put('receipt', receipt);
    return receipt;
  }
}
async function authorized(request, env) {
  if (!env.OPS_TOKEN) return false;
  const expected = new TextEncoder().encode('Bearer ' + env.OPS_TOKEN);
  const actual = new TextEncoder().encode(request.headers.get('Authorization') || '');
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(env.OPS_TOKEN), {name: 'HMAC', hash: 'SHA-256'}, false, ['sign', 'verify']);
  const signature = await crypto.subtle.sign('HMAC', key, expected);
  return crypto.subtle.verify('HMAC', key, signature, actual);
}
function json(value, status = 200) { return Response.json(value, {status, headers: {'Cache-Control': 'no-store'}}); }
export async function handleGate(request, store, env) {
    if (request.method === 'GET') return json(await store.get(new URL(request.url).pathname === '/probe' ? 'probe' : 'receipt') || null);
    const input = await request.json();
    if (input.kind === 'probe') {
      if (request.method === 'POST') await store.put('probe', {scheduled_time: input.scheduled_time, observed_at: new Date().toISOString(), deployment_id: input.deployment_id});
      return json(await store.get('probe') || null);
    }
    return json(await dispatchOnce(store, env, input));
}
function gate(env, key) { return env.DAILY_GATE.get(env.DAILY_GATE.idFromName(key)); }
async function send(env, key, payload) { return (await gate(env, key).fetch('https://internal/dispatch', {method: 'POST', body: JSON.stringify(payload)})).json(); }
export async function scheduledTick(controller, env, now = Date.now()) {
  if (env.PROBE_ONLY === 'true') return send(env, 'probe:' + env.DEPLOYMENT_ID, {kind: 'probe', scheduled_time: new Date(controller.scheduledTime).toISOString(), deployment_id: env.DEPLOYMENT_ID});
  if (env.DISPATCH_ENABLED !== 'true') return {status: 'disabled'};
  const operation = clockOperation(controller.scheduledTime, now);
  if (!operation) return {status: 'wrong_timezone_or_expired_trigger'};
  const results = [];
  for (const repo of REPOS) {
    try { results.push(await send(env, `${operation.kind}:${operation.day}:${repo}`, {...operation, repo})); }
    catch (error) { results.push({repo, phase: 'preflight_unavailable_no_dispatch', ...(error.httpStatus ? {http_status: error.httpStatus} : {})}); }
  }
  console.log(JSON.stringify({kind: operation.kind, day: operation.day, results}));
  return results;
}
export async function handleRequest(request, env) {
    if (!(await authorized(request, env))) return new Response('Not found', {status: 404});
    const path = new URL(request.url).pathname;
    if (request.method === 'GET' && path === '/_ops/clock-probe') {
      return gate(env, 'probe:' + env.DEPLOYMENT_ID).fetch('https://internal/probe');
    }
    if (request.method === 'POST' && path === '/_ops/test-dispatch') {
      const day = local(Date.now()).day, results = [];
      for (const repo of REPOS) results.push(await send(env, `test:${env.DEPLOYMENT_ID}:${day}:${repo}`, {repo, day, kind: 'test'}));
      return json({dry_run: true, results});
    }
    return new Response('Not found', {status: 404});
}
