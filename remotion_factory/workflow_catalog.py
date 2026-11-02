"""Disable explicitly retired workflow IDs; preserve every historical run/artifact."""
import json,os,sys
from pathlib import Path
from .health import gh,write_json,AuditFailure

def main():
 request=json.loads(Path('.github/remotion-cleanup-request.json').read_text());keep=set(request['keep_paths']);retired=set(request['retired_paths'])
 if not keep or keep&retired:raise AuditFailure('Invalid current/retired workflow plan')
 head=gh('/git/ref/heads/main')['object']['sha'];tree=gh('/git/trees/'+head+'?recursive=1')
 if tree.get('truncated'):raise AuditFailure('Cannot verify incomplete workflow tree')
 paths={item['path'] for item in tree['tree']}
 if not keep<=paths or retired&paths:raise AuditFailure('Active files missing or retired workflow file still exists on main')
 rows=[]
 for page in range(1,6):
  batch=gh('/actions/workflows?per_page=100&page='+str(page))['workflows'];rows.extend(batch)
  if len(batch)<100:break
 else:raise AuditFailure('Incomplete workflow catalog')
 report={'head':head,'run_id':os.environ['GITHUB_RUN_ID'],'disabled':[],'active':[],'unknown_preserved':[],'errors':[],'run_deletions':0,'artifact_deletions':0,'social_mutations':0,'generation_calls':0}
 for row in rows:
  path=row['path']
  if path in keep:
   if row['state']!='active':report['errors'].append('Required workflow is not active: '+path)
   report['active'].append({k:row[k] for k in ('id','name','path','state')});continue
  if path not in retired:
   report['unknown_preserved'].append({k:row[k] for k in ('id','name','path','state')})
   if row['state']=='active':report['errors'].append('Unexpected active workflow outside current plan: '+path)
   continue
  if row['state']=='active':gh('/actions/workflows/'+str(row['id'])+'/disable','PUT')
  actual=gh('/actions/workflows/'+str(row['id']))
  if actual['state']=='active':report['errors'].append('Retired workflow remains active: '+path)
  else:report['disabled'].append({k:actual[k] for k in ('id','name','path','state')})
 report['passed']=not report['errors'];write_json('reviews/cleanup/workflow-catalog-'+os.environ['GITHUB_RUN_ID']+'.json',report);write_json('reviews/cleanup/workflow-catalog-latest.json',report)
 Path('cleanup-output').mkdir(exist_ok=True);Path('cleanup-output/workflow-catalog.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
 if not report['passed']:sys.exit(1)

if __name__=='__main__':main()
