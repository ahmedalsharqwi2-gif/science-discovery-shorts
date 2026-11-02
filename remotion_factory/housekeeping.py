"""One-off conservative cleanup, with verified recovery refs and atomic delete leases."""
import base64,json,os,re,subprocess,sys,time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import quote
from .state import identity
from .health import gh,write_json,instant,AuditFailure
SNAPSHOT=re.compile(r'^codex/(?:professional-review-run|professional-video|octopus-review-run|destination-check|planning-diagnostic|editorial-models|history-sources|gemini-feature-plan|motion-scene-review|voice-sample|voice-tests|voicetut-sample|feature-voices|abu-simbel-(?:feature|polished|review)|audio-tail-fixed|listening-pack|number-word-review|motion-(?:720|delivery|preview)|neural-clarity|voice-catalogue|voice-lab)-(\d+)$')
def paged(path,key=None):
 out=[]
 for page in range(1,11):
  result=gh(path+('&' if '?' in path else '?')+f'per_page=100&page={page}') or ([] if key is None else {})
  rows=result.get(key,[]) if key else result;out.extend(rows)
  if len(rows)<100:return out
 raise AuditFailure('Inventory pagination bound reached; no incomplete cleanup')
def category(name,protected,default,workflow_text,open_heads,active_heads):
 if protected or name in {default,'main','master'}:return 'keep_protected_or_default'
 if name.startswith(('codex/rebuild-production-v2','codex/production-v2-')):return 'keep_recovery_and_diagnostic_history'
 if name in open_heads:return 'keep_open_pull_request'
 if name in active_heads:return 'keep_active_run'
 if name in workflow_text:return 'keep_workflow_reference'
 return 'snapshot' if SNAPSHOT.fullmatch(name) else 'check_merged'
def disposable(path):
 if path.startswith(('state/','reviews/','.github/','.agents/','.codex/')):return False
 parts=Path(path).parts
 return '__pycache__' in parts or '.pytest_cache' in parts or path.endswith(('.pyc','.pyo','/.DS_Store')) or path=='.DS_Store'
def archive(tag,sha):
 path='/git/ref/tags/'+quote(tag,safe='/');existing=gh(path)
 if existing:
  if existing['object']['sha']!=sha:raise AuditFailure('Archive tag already points elsewhere; never overwrite it')
 else:gh('/git/refs','POST',{'ref':'refs/tags/'+tag,'sha':sha})
 # A newly created ref can briefly return404. Retry only verification, never deletion or creation.
 proof=None
 for attempt in range(6):
  proof=gh(path+'?verify_attempt='+str(attempt))
  if proof:
   if proof['object']['sha']!=sha:raise AuditFailure('Recovery ref points elsewhere; preserve the branch')
   break
  if attempt<5:time.sleep(1)
 if not proof:raise AuditFailure('Recovery ref not independently confirmed; branch preserved')
 return tag
def remove_cache(paths):
 if not paths:return None
 for attempt in range(3):
  head=gh('/git/ref/heads/main')['object']['sha'];commit=gh('/git/commits/'+head);tree=gh('/git/trees/'+commit['tree']['sha']+'?recursive=1')
  if tree.get('truncated'):raise AuditFailure('Refuse cleanup using a truncated source tree')
  blobs={i['path']:i for i in tree['tree'] if i['type']=='blob'};entries=[]
  for item in paths:
   current=blobs.get(item['path'])
   if not current:continue
   if current['sha']!=item['sha'] or not disposable(item['path']):raise AuditFailure('A planned cache path changed; preserve it for inspection')
   entries.append({'path':item['path'],'mode':current['mode'],'type':'blob','sha':None})
  old=gh('/contents/.gitignore?ref=main');ignore=base64.b64decode(old['content']).decode() if old else ''
  additions=[p for p in ('__pycache__/','*.py[cod]','.pytest_cache/','.DS_Store') if p not in ignore.splitlines()]
  if additions:entries.append({'path':'.gitignore','mode':'100644','type':'blob','content':ignore.rstrip()+'\n\n# Generated caches; source, voice records and receipts stay tracked.\n'+'\n'.join(additions)+'\n'})
  if not entries:return None
  new_tree=gh('/git/trees','POST',{'base_tree':commit['tree']['sha'],'tree':entries});new=gh('/git/commits','POST',{'message':'Remove only generated tracked caches after verified recovery archive [skip ci]','tree':new_tree['sha'],'parents':[head]})
  try:gh('/git/refs/heads/main','PATCH',{'sha':new['sha'],'force':False});return new['sha']
  except AuditFailure:
   if attempt==2:raise
def main():
 repo,_=identity();event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());request=json.loads(Path('.github/remotion-cleanup-request.json').read_text());apply=event.get('inputs',{}).get('apply',False) if os.getenv('GITHUB_EVENT_NAME')=='workflow_dispatch' else request.get('apply',False);apply=apply is True or str(apply).lower()=='true';now=datetime.now(timezone.utc);run=os.environ['GITHUB_RUN_ID'];prefix='archive/housekeeping-'+run+'-'+os.getenv('GITHUB_RUN_ATTEMPT','1');report={'repository':repo,'run_id':run,'apply':apply,'started_at':now.isoformat(),'errors':[],'deleted_branches':[],'retained':[],'removed_paths':[],'generation_calls':0,'social_mutations':0}
 Path('cleanup-output').mkdir(exist_ok=True)
 try:
  meta=gh('');default=meta['default_branch'];head=gh('/git/ref/heads/'+quote(default,safe='/'))['object']['sha'];root=gh('/git/commits/'+head);tree=gh('/git/trees/'+root['tree']['sha']+'?recursive=1')
  if tree.get('truncated'):raise AuditFailure('Truncated tracked-path inventory; no cleanup')
  branches=paged('/branches');pulls=paged('/pulls?state=open');open_heads={p['head']['ref'] for p in pulls};active_heads=set()
  for state in ('queued','in_progress','waiting','requested','pending'):
   active_heads.update(r['head_branch'] for r in paged('/actions/runs?status='+state,'workflow_runs'))
  workflow_text='\n'.join(p.read_text() for p in Path('.github/workflows').glob('*') if p.is_file())
  candidates=[]
  for branch in branches:
   name=branch['name'];sha=branch['commit']['sha'];kind=category(name,branch.get('protected',False),default,workflow_text,open_heads,active_heads)
   if kind.startswith('keep_'):report['retained'].append({'name':name,'reason':kind});continue
   commit=gh('/git/commits/'+sha)
   if not commit or instant(commit['committer']['date'])>now-timedelta(hours=24):report['retained'].append({'name':name,'reason':'keep_recent_commit_under24hours'});continue
   if kind=='snapshot':
    match=SNAPSHOT.fullmatch(name);old_run=gh('/actions/runs/'+match.group(1))
    if not old_run or old_run['status']!='completed' or instant(old_run['created_at'])>now-timedelta(hours=24):report['retained'].append({'name':name,'reason':'keep_recent_or_unverified_run_snapshot'});continue
    reason='completed_run_snapshot_older_than24hours_not_referenced'
   else:
    comparison=gh('/compare/'+sha+'...'+head+'?per_page=1')
    if not comparison or comparison.get('behind_by')!=0:report['retained'].append({'name':name,'reason':'keep_unmerged_work_not_proven_unused'});continue
    reason='fully_merged_into_current_main_and_inactive'
   candidates.append({'name':name,'sha':sha,'reason':reason})
  paths=[{'path':i['path'],'sha':i['sha'],'bytes':i.get('size',0)} for i in tree['tree'] if i['type']=='blob' and disposable(i['path'])]
  report.update(default_branch=default,main_before=head,branch_count=len(branches),planned_branches=candidates,planned_paths=paths)
  if apply:
   report['main_recovery_tag']=archive(prefix+'/main-before-cleanup',head)
   for item in candidates:
    name=item['name'];current=gh('/git/ref/heads/'+quote(name,safe='/'))
    if not current or current['object']['sha']!=item['sha']:report['retained'].append({'name':name,'reason':'ref_changed_after_inventory'});continue
    tag=archive(prefix+'/'+name,item['sha'])
    # Git's expected old OID is checked atomically by the server even on deletion.
    deleted=subprocess.run(['git','push','--porcelain','--force-with-lease=refs/heads/'+name+':'+item['sha'],'origin',':refs/heads/'+name],capture_output=True,text=True)
    actual=gh('/git/ref/heads/'+quote(name,safe='/'))
    if actual is None:report['deleted_branches'].append({**item,'recovery_tag':tag})
    else:report['errors'].append('Branch preserved after rejected/changed deletion: '+name)
   report['cache_cleanup_commit']=remove_cache(paths);report['removed_paths']=paths
  report['passed']=not report['errors']
 except Exception as exc:report['passed']=False;report['errors'].append(str(exc) if isinstance(exc,AuditFailure) else type(exc).__name__)
 report['finished_at']=datetime.now(timezone.utc).isoformat();Path('cleanup-output/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');path='reviews/cleanup/'+run+'-'+os.getenv('GITHUB_RUN_ATTEMPT','1')+'.json'
 try:write_json(path,report);write_json('reviews/cleanup/latest.json',report)
 except Exception as exc:report['passed']=False;report['errors'].append('Could not preserve cleanup report: '+type(exc).__name__);Path('cleanup-output/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 summary={'passed':report['passed'],'apply':apply,'planned_branches':len(report.get('planned_branches',[])),'deleted_branches':len(report['deleted_branches']),'planned_generated_paths':len(report.get('planned_paths',[])),'removed_generated_paths':len(report['removed_paths']),'retained_branches':len(report['retained']),'errors':report['errors']};print(json.dumps(summary))
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## Repository cleanup\n\n```json\n'+json.dumps(summary,indent=2)+'\n```\n\nRecovery records: '+path+'\n')
 if not report['passed']:sys.exit(1)
if __name__=='__main__':main()
