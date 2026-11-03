import test from 'node:test';
import assert from 'node:assert/strict';
import {handleGate, handleRequest, REPOS, local, clockOperation, dispatchOnce, scheduledTick} from './core.mjs';
const winter = Date.parse('2030-01-03T07:00:00Z');
const env = {GITHUB_DISPATCH_TOKEN: 'test-only-credential', OPS_TOKEN: 'test-only-ops', DEPLOYMENT_ID: 'tests'};
class Store {
  constructor() { this.values = new Map(); this.lock = Promise.resolve(); }
  async get(k) { return this.values.get(k); }
  async put(k, v) { this.values.set(k, structuredClone(v)); }
  transaction(fn) { const next = this.lock.then(() => fn(this)); this.lock = next.catch(() => {}); return next; }
}
function apiMock({rows = [], failedRead, failedPost, networkUnknown = false, paginated = false} = {}) {
  const calls = [];
  const http = async (url, options) => {
    calls.push({url, ...options});
    if (options.method === 'POST') {
      if (networkUnknown) throw new Error('connection reset after sending');
      return new Response(null, {status: failedPost || 204});
    }
    return Response.json({workflow_runs: paginated ? Array.from({length: 100}, (_, n) => ({id: n, created_at: '2030-01-03T06:00:00Z'})) : rows}, {status: failedRead || 200});
  };
  return {http, calls, posts: () => calls.filter(c => c.method === 'POST')};
}
const operation = {repo: REPOS[0], day: '2030-01-03', kind: 'production'};
test('Cairo winter/summer scheduling and same-day keys', () => {
  assert.deepEqual(local(winter), {day: '2030-01-03', hour: 9, minute: 0});
  assert.deepEqual(clockOperation(winter, winter), {kind: 'production', day: '2030-01-03'});
  const summer = Date.parse('2030-07-03T06:17:00Z');
  assert.deepEqual(clockOperation(summer, summer), {kind: 'production', day: '2030-07-03'});
  assert.equal(clockOperation(winter - 3600000, winter - 3600000), null);
});
test('missed/late production cannot roll over or launch at midday', () => {
  assert.equal(clockOperation(winter, winter + 86400000), null);
  assert.equal(clockOperation(winter, winter + 3600000), null);
});
test('post-publication audit is at17:35 Cairo', () => {
  const t = Date.parse('2030-01-03T15:35:00Z');
  assert.deepEqual(clockOperation(t, t), {kind: 'publication-audit', day: '2030-01-03'});
});
test('one dispatch uses only the existing workflow and explicit same-day date', async () => {
  const store = new Store(), api = apiMock();
  const receipt = await dispatchOnce(store, env, operation, api.http, winter);
  assert.equal(receipt.phase, 'dispatch_accepted');
  assert.equal(receipt.production_completion_claimed, false);
  assert.equal(api.posts().length, 1);
  assert.deepEqual(JSON.parse(api.posts()[0].body), {ref: 'main', inputs: {publish_date: '2030-01-03', dry_run: false, trigger_source: 'cloudflare-clock'}});
  assert.ok(api.calls.every(c => c.url.startsWith('https://api.github.com/repos/ahmedalsharqwi2-gif/')));
});
test('primary plus backup plus concurrent duplicate execute one dispatch', async () => {
  const store = new Store(), api = apiMock();
  await Promise.all(Array.from({length: 8}, () => dispatchOnce(store, env, operation, api.http, winter)));
  await dispatchOnce(store, env, operation, api.http, winter + 17 * 60000);
  assert.equal(api.posts().length, 1);
});
test('a lost acknowledgement is retained and never resent', async () => {
  const store = new Store(), api = apiMock({networkUnknown: true});
  assert.equal((await dispatchOnce(store, env, operation, api.http, winter)).phase, 'dispatch_uncertain');
  await dispatchOnce(store, env, operation, api.http, winter + 17 * 60000);
  assert.equal(api.posts().length, 1);
});
test('an already retained intent is never retried', async () => {
  const store = new Store(), api = apiMock(); await store.put('receipt', {phase: 'intent'});
  assert.equal((await dispatchOnce(store, env, operation, api.http, winter)).phase, 'intent');
  assert.equal(api.calls.length, 0);
});
test('existing queued/in-progress/success/failed current-day runs are preserved', async () => {
  for (const [status, conclusion] of [['queued', null], ['in_progress', null], ['completed', 'success'], ['completed', 'failure']]) {
    const api = apiMock({rows: [{id: 123, status, conclusion, created_at: '2030-01-03T07:00:01Z'}]});
    const receipt = await dispatchOnce(new Store(), env, operation, api.http, winter + 5000);
    assert.equal(receipt.run_id, 123); assert.equal(api.posts().length, 0);
  }
});
test('the opposite-DST no-op before9 does not suppress the real clock', async () => {
  const api = apiMock({rows: [{id: 1, status: 'completed', conclusion: 'success', created_at: '2030-01-03T06:00:00Z'}]});
  await dispatchOnce(new Store(), env, operation, api.http, winter);
  assert.equal(api.posts().length, 1);
});
test('failed/incomplete discovery never starts production', async () => {
  for (const config of [{failedRead: 403}, {paginated: true}]) {
    const api = apiMock(config);
    await assert.rejects(dispatchOnce(new Store(), env, operation, api.http, winter));
    assert.equal(api.posts().length, 0);
  }
});
test('test dispatch is always dry-run and cannot claim production', async () => {
  const api = apiMock();
  await dispatchOnce(new Store(), env, {...operation, kind: 'test'}, api.http, winter + 2 * 3600000);
  const body = JSON.parse(api.posts()[0].body);
  assert.equal(body.inputs.dry_run, true); assert.equal(body.inputs.trigger_source, 'cloudflare-clock-test');
});
test('audit dispatch only calls the read-only health workflow', async () => {
  const api = apiMock(), t = Date.parse('2030-01-03T15:35:00Z');
  await dispatchOnce(new Store(), env, {...operation, kind: 'publication-audit'}, api.http, t);
  assert.match(api.posts()[0].url, /remotion-health.yml\/dispatches$/);
  assert.deepEqual(JSON.parse(api.posts()[0].body).inputs, {date: '2030-01-03', phase: 'postpublish'});
});
test('a completed earlier failed audit does not suppress the independent read-only recheck', async () => {
  const api = apiMock({rows: [{id: 77, status: 'completed', conclusion: 'failure', created_at: '2030-01-03T15:30:00Z'}]});
  await dispatchOnce(new Store(), env, {...operation, kind: 'publication-audit'}, api.http, Date.parse('2030-01-03T15:35:00Z'));
  assert.equal(api.posts().length, 1);
  assert.match(api.posts()[0].url, /remotion-health.yml\/dispatches$/);
});
test('unknown repository, cross-day, late production and missing credential are rejected', async () => {
  const api = apiMock();
  for (const [input, credential, now] of [[{...operation, repo: 'someone-else'}, env, winter], [{...operation, day: '2030-01-02'}, env, winter], [operation, env, winter + 2 * 3600000], [operation, {}, winter]]) {
    await assert.rejects(dispatchOnce(new Store(), credential, input, api.http, now));
  }
  assert.equal(api.posts().length, 0);
});
test('public HTTP cannot trigger, read state, or leak a secret', async () => {
  for (const path of ['/', '/_ops/test-dispatch', '/_ops/clock-probe']) {
    const response = await handleRequest(new Request('https://clock.example' + path), env);
    assert.equal(response.status, 404);
    assert.ok(!(await response.text()).includes(env.GITHUB_DISPATCH_TOKEN));
  }
});
test('live-clock probe stores only a tick and never calls GitHub', async () => {
  const store = new Store(), state = {storage: store};
  const actor = {fetch: request => handleGate(request, store, env)};
  const bound = {idFromName: x => x, get: () => ({fetch: (url, options) => actor.fetch(new Request(url, options))})};
  await scheduledTick({scheduledTime: winter}, {...env, PROBE_ONLY: 'true', DAILY_GATE: bound}, winter);
  const response = await actor.fetch(new Request('https://internal/probe'));
  assert.equal((await response.json()).deployment_id, env.DEPLOYMENT_ID);
  assert.equal(await store.get('receipt'), undefined);
});
