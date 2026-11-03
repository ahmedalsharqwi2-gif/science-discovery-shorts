// Read-only check of existing GitHub repository secrets. Never logs their values.
import {writeFile} from 'node:fs/promises';
const account = (process.env.CLOUDFLARE_ACCOUNT_ID || '').trim();
const token = (process.env.CLOUDFLARE_API_TOKEN || '').trim();
const report = {read_only: true, cloudflare_account_present: !!account, cloudflare_token_present: !!token, account_id_format_valid: /^[a-f0-9]{32}$/i.test(account), github_dispatch_token_present: process.env.HAS_FACTORY_DISPATCH_TOKEN === 'true', cloudflare_mutations: 0, generation_calls: 0, publication_calls: 0, checked_at: new Date().toISOString()};
if (token && report.account_id_format_valid) {
  const check = async (name, path) => {
    try {
      const response = await fetch(`https://api.cloudflare.com/client/v4/accounts/${account}${path}`, {headers: {Authorization: 'Bearer ' + token}, signal: AbortSignal.timeout(30000)});
      const body = await response.json();
      const result = {http_status: response.status, authenticated_read_succeeded: response.ok && body.success === true};
      if (name === 'workers_scripts' && result.authenticated_read_succeeded && Array.isArray(body.result)) result.clock_worker_already_exists = body.result.some(worker => worker.id === 'video-factory-cairo-clock');
      if (name === 'clock_settings' && result.authenticated_read_succeeded) {
        result.probe_only = body.result?.bindings?.find(b => b.name === 'PROBE_ONLY')?.text;
        result.dispatch_enabled = body.result?.bindings?.find(b => b.name === 'DISPATCH_ENABLED')?.text;
      }
      if (name === 'clock_schedules' && result.authenticated_read_succeeded) {
        const schedules = body.result?.schedules || body.result || [];
        result.registered_crons = Array.isArray(schedules) ? schedules.map(s => s.cron) : null;
      }
      if (name === 'workers_subdomain' && result.authenticated_read_succeeded) result.configured = Boolean(body.result?.subdomain);
      return [name, result];
    } catch { return [name, {authenticated_read_succeeded: false, transport_unavailable: true}]; }
  };
  Object.assign(report, Object.fromEntries(await Promise.all([check('account_settings', ''), check('workers_scripts', '/workers/scripts'), check('clock_settings', '/workers/scripts/video-factory-cairo-clock/settings'), check('clock_schedules', '/workers/scripts/video-factory-cairo-clock/schedules'), check('workers_subdomain', '/workers/subdomain')])));
}
report.passed = report.account_settings?.authenticated_read_succeeded === true && report.workers_scripts?.authenticated_read_succeeded === true;
report.workers_write_permission_claimed = false;
await writeFile(new URL('./credential-probe.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (!report.passed) process.exitCode = 1;
