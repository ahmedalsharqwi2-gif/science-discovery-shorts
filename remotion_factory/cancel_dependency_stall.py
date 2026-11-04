"""Cancel only a pinned dependency stall, never a started generative stage."""
import json,os,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
PINS={'ahmedalsharqwi2-gif/science-discovery-shorts':(41904494022,126875514633),'ahmedalsharqwi2-gif/arabic-horror-stories':(41904549127,126875592961)}
def eligible(job,run,ledger,now):
 active=[s for s in job.get('steps',[]) if s.get('status')=='in_progress']
 if job.get('run_id')!=run or job.get('status')!='in_progress' or len(active)!=1 or active[0]['name']!='Install planning prerequisites':raise ValueError('Only a verified dependency-only stall can cancel')
 for name in ['Freeze original date; verify configured Cairo clock and existing queues','New topic → retained voice → Remotion → full decode → verified configured-time scheduling']:
  rows=[s for s in job['steps'] if s.get('name')==name]
  if len(rows)!=1 or rows[0].get('status') not in ('queued','pending'):raise ValueError('Planning or generation already started')
 for entry in ledger.get('episodes',{}).values():
  if entry.get('source_run')==run and (entry.get('status')!='author_pending' or any(entry.get(k) for k in ('writer_run','voice_request_run','render_run','receipts'))):raise ValueError('Retained work has progressed')
  if any(entry.get(k)==run for k in ('writer_run','voice_request_run','render_run')):raise ValueError('Paid work recorded')
 started=datetime.fromisoformat(active[0]['started_at'].replace('Z','+00:00'))
 if (now-started).total_seconds()<480:raise ValueError('Installer has not exceeded eight minutes')
 return True
def main():
 req=json.loads(Path('.github/remotion-cleanup-request.json').read_text());repo=os.environ['GITHUB_REPOSITORY']
 if repo not in PINS or (req.get('run_id'),req.get('expected_job_id'))!=PINS[repo] or req.get('operation')!='cancel-stuck-prerequisites' or not req.get('approved_by_owner'):raise ValueError('Exact cancellation-only request required')
 run,jobid=PINS[repo]
 def gh(path,method='GET'):
  request=Request('https://api.github.com/repos/'+repo+path,method=method,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','User-Agent':'dependency-only-recovery'})
  with urlopen(request,timeout=30) as response:return json.loads(response.read() or '{}')
 info=gh('/actions/runs/'+str(run));proof={'run_id':run,'new_runs':0,'publication_mutations':0,'generation_calls':0}
 if info['status']=='completed':proof['already_completed']=info.get('conclusion')
 else:
  if info.get('path')!='.github/workflows/remotion-daily.yml':raise ValueError('Wrong production workflow')
  job=gh('/actions/jobs/'+str(jobid));eligible(job,run,json.loads(Path('state/remotion_registry.json').read_text()),datetime.now(timezone.utc))
  gh('/actions/runs/'+str(run)+'/cancel','POST');proof['cancel_accepted']=True
 Path('cleanup-output').mkdir(exist_ok=True);Path('cleanup-output/dependency-only-cancellation.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))
if __name__=='__main__':main()
