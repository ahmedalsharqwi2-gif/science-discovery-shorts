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
      return [name, result];
    } catch { return [name, {authenticated_read_succeeded: false, transport_unavailable: true}]; }
  };
  Object.assign(report, Object.fromEntries(await Promise.all([check('account_settings', ''), check('workers_scripts', '/workers/scripts')])));
}
report.passed = report.account_settings?.authenticated_read_succeeded === true && report.workers_scripts?.authenticated_read_succeeded === true;
report.workers_write_permission_claimed = false;
await writeFile(new URL('./credential-probe.json', import.meta.url), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (!report.passed) process.exitCode = 1;
