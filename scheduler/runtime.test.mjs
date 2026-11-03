import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare, convertV4MiniflareOptions} from 'miniflare';
import {REPOS, local} from './core.mjs';
import {readFile} from 'node:fs/promises';

test('real Cloudflare runtime: SQLite Durable Objects, authenticated dry dispatch and persistent duplicate gate', async () => {
  let posts = 0;
  const fixedTime = Date.parse('2030-01-03T07:00:00Z');
  const bundle = await readFile(new URL('./dist/worker.js', import.meta.url), 'utf8');
  const mf = new Miniflare(convertV4MiniflareOptions({workers: [{
    name: 'clock-runtime-test',
    modules: true, script: `Date.now = () => ${fixedTime};\n${bundle}`,
    compatibilityDate: '2025-05-01',
    bindings: {FACTORY_DISPATCH_TOKEN: 'local-test-only', OPS_TOKEN: 'local-ops-only', DEPLOYMENT_ID: 'runtime-test', PROBE_ONLY: 'true', DISPATCH_ENABLED: 'false'},
    durableObjects: {DAILY_GATE: {className: 'DailyGate', useSQLite: true}},
    outboundService: async request => {
      assert.ok(request.url.startsWith('https://api.github.com/'));
      if (request.method === 'POST') {
        const body = await request.json();
        assert.equal(body.inputs.dry_run, true);
        assert.equal(body.inputs.trigger_source, 'cloudflare-clock-test');
        assert.equal(body.inputs.publish_date, local(fixedTime).day);
        posts++; return new Response(null, {status: 204});
      }
      throw new Error('Unexpected outbound request');
    }
  }]}));
  try {
    await mf.ready;
    const request = () => mf.dispatchFetch('https://clock.local/_ops/test-dispatch', {method: 'POST', headers: {Authorization: 'Bearer local-ops-only'}});
    const first = await request(); assert.equal(first.status, 200);
    const results = (await first.json()).results;
    assert.equal(results.length, 5); assert.ok(results.every(r => r.phase === 'dispatch_accepted' && r.dry_run));
    const second = await request(); assert.equal(second.status, 200); assert.equal(posts, 5);
    assert.equal((await mf.dispatchFetch('https://clock.local/_ops/clock-probe')).status, 404);
    const ns = await mf.getDurableObjectNamespace('DAILY_GATE');
    const id = ns.idFromName('probe:runtime-test');
    const actor = ns.get(id);
    await actor.fetch('https://internal/probe', {method: 'POST', body: JSON.stringify({kind: 'probe', deployment_id: 'runtime-test', scheduled_time: new Date().toISOString()})});
    const probe = await mf.dispatchFetch('https://clock.local/_ops/clock-probe', {headers: {Authorization: 'Bearer local-ops-only'}});
    assert.equal((await probe.json()).deployment_id, 'runtime-test');
    assert.equal(REPOS.length, posts);
  } finally { await mf.dispose(); }
});
