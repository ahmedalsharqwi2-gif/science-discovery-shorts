// Provider reads and one own-repository health issue only. Never generates or posts.
import {readFile, writeFile} from 'node:fs/promises';
import {sourceDigest} from './source-digest.mjs';
import {normalizePolicy, cronExpressions, releasePlan, shiftDay} from './schedule-policy.mjs';
import {OWNER, REPOS, local} from './core.mjs';
const repo = OWNER + '/science-discovery-shorts';
const report = {checked_at:new Date().toISOString(), read_only_provider:true, generation_calls:0, publication_mutations:0, errors:[], repositories:{}};
async function cf(path) {
  const response = await fetch(`https://api.cloudflare.com/client/v4/accounts/${process.env.CLOUDFLARE_ACCOUNT_ID}${path}`, {headers:{Authorization:'Bearer '+process.env.CLOUDFLARE_API_TOKEN},signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error('Cloudflare audit HTTP '+response.status);
  const data = await response.json(); if (!data.success) throw new Error('Cloudflare audit not confirmed'); return data.result;
}
async function publicJSON(path) {
  const response = await fetch('https://raw.githubusercontent.com/'+path, {signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error('Public repository audit HTTP '+response.status); return response.json();
}
try {
  const config = JSON.parse(await readFile(new URL('./wrangler.json',import.meta.url),'utf8'));
  const policy = normalizePolicy(JSON.parse(await readFile(new URL('../config/remotion_daily_release.json',import.meta.url),'utf8')));
  const expected = await sourceDigest();
  const [settings, schedules] = await Promise.all([cf('/workers/scripts/'+config.name+'/settings'),cf('/workers/scripts/'+config.name+'/schedules')]);
  const binding = key => settings?.bindings?.find(b => b.name===key)?.text;
  report.deployment_id=binding('DEPLOYMENT_ID'); report.live_source_sha256=binding('SOURCE_SHA256') || null; report.expected_source_sha256=expected;
  report.actual_crons=(schedules?.schedules || schedules || []).map(s => s.cron); report.expected_crons=cronExpressions(policy);
  if (report.live_source_sha256!==expected) report.errors.push('Live Cloudflare source differs from the repository');
  if (binding('DISPATCH_ENABLED')!=='true' || binding('PROBE_ONLY')!=='false') report.errors.push('Live production clock is not enabled');
  if (binding('SCHEDULE_POLICY')!==JSON.stringify(policy)) report.errors.push('Live Cloudflare release policy differs from the repository');
  if (JSON.stringify([...report.actual_crons].sort())!==JSON.stringify([...report.expected_crons].sort())) report.errors.push('Live Cloudflare cron registration differs from the release policy');
  const now=local(Date.now()), tomorrow=shiftDay(now.day,1);
  const dueDay=[tomorrow,now.day].find(day => {const p=releasePlan(day,policy);return p.preparationDay===now.day && now.hour*60+now.minute>=p.productionHour*60+30;});
  report.production_audit_target=dueDay || null;
  for (const name of REPOS) {
    const observed = await publicJSON(`${OWNER}/${name}/main/config/remotion_daily_release.json`);
    const result=report.repositories[name]={policy_matches:JSON.stringify(normalizePolicy(observed))===JSON.stringify(policy)};
    if (!result.policy_matches) report.errors.push(name+': release policy differs from shared clock');
    if (dueDay) {
      const ledger = await publicJSON(`${OWNER}/${name}/main/state/remotion_registry.json`);
      const rows=Object.values(ledger.episodes || {}).filter(e => e.due_at && local(e.due_at).day===dueDay && e.status==='scheduled' && e.video_sha256 && e.media_url && Object.values(e.receipts || {}).filter(r=>r.id && r.phase==='verified').length===3);
      result.retained_complete_film_and_three_receipts=rows.length===1;
      if (!result.retained_complete_film_and_three_receipts) report.errors.push(name+': no unique completed film with three retained scheduling receipts for '+dueDay);
    }
  }
} catch (error) {report.errors.push(error.message);}
report.passed=report.errors.length===0;
await writeFile(new URL('./live-audit.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
// Keep one incident, change it only when the incident state changes.
if (process.env.GITHUB_TOKEN) {
  try {
    const gh=async(path,method='GET',body)=>{
      const response=await fetch(`https://api.github.com/repos/${repo}${path}`,{method,headers:{Authorization:'Bearer '+process.env.GITHUB_TOKEN,Accept:'application/vnd.github+json','Content-Type':'application/json','User-Agent':'factory-clock-audit'},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(30000)});
      if(!response.ok)throw new Error('GitHub alert HTTP '+response.status);return response.status===204?{}:response.json();
    };
    const marker='<!-- factory-independent-clock-drift -->';
    const issues=await gh('/issues?state=all&per_page=100');
    const old=issues.find(i=>!i.pull_request && (i.body || '').startsWith(marker));
    const title='Independent production clock — live schedule and readiness';
    const body=marker+'\n'+(report.passed?'Live clock and retained production evidence verified.':report.errors.map(e=>'- '+e).join('\n'))+'\n\nRead-only audit; never automatically regenerates, resubmits or rolls a missed slot forward.';
    if(old){const state=report.passed?'closed':'open';if(old.state!==state || old.body!==body)await gh('/issues/'+old.number,'PATCH',{state,body});}
    else if(!report.passed)await gh('/issues','POST',{title,body});
  } catch(error){console.error(error.message);process.exitCode=1;}
}
if(!report.passed)process.exitCode=1;
