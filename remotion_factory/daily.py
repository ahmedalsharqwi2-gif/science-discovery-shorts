"""Cairo civil-time daily controller. Each run keeps its original publication date."""
import argparse,hashlib,io,json,os,subprocess,sys,zipfile
from datetime import datetime,timedelta,time,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from .state import identity,mutate
from .publish import destinations,queued,instant
CAIRO=ZoneInfo('Africa/Cairo')
ROOT=Path('professional_motion/delivery')
def command(*args):subprocess.run(list(args),check=True)
def slot_for(created,event,schedule='',target=None,now=None):
 now=now or datetime.now(timezone.utc);local=created.astimezone(CAIRO)
 if event=='schedule':
  expected='0 '+str(9-int(local.utcoffset().total_seconds()/3600))+' * * *'
  if schedule!=expected or not 9<=local.hour<13:return None
 day=datetime.fromisoformat(target).date() if target else local.date()+timedelta(days=1)
 due=datetime.combine(day,time(17),CAIRO).astimezone(timezone.utc)
 if due<=now:raise ValueError('Original publication time expired; no automatic rollover')
 return due
def api(path):
 repo,_=identity();r=requests.get('https://api.github.com/repos/'+repo+path,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'},timeout=40);r.raise_for_status();return r.json()
def extract(run,prefix,target):
 rows=api(f'/actions/runs/{run}/artifacts')['artifacts'];rows=[a for a in rows if not a['expired'] and a['name'].startswith(prefix)]
 if not rows:raise RuntimeError('Retained request has no recoverable artifact; repeated generation forbidden')
 row=max(rows,key=lambda r:r['id']);repo,_=identity();r=requests.get(row['archive_download_url'],headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN']},timeout=180);r.raise_for_status()
 with zipfile.ZipFile(io.BytesIO(r.content)) as archive:
  if sum(i.file_size for i in archive.infolist())>2_000_000_000:raise ValueError('Artifact exceeds production bound')
  for item in archive.infolist():
   p=Path(item.filename)
   if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe artifact path')
  archive.extractall(target)
 return row['id']
def decide(args):
 repo,profile=identity();event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text());created=instant(api('/actions/runs/'+os.environ['GITHUB_RUN_ID'])['created_at'])
 target=args.date or event.get('inputs',{}).get('publish_date') or None
 request=Path('.github/remotion-daily-request.json')
 if os.environ['GITHUB_EVENT_NAME']=='push' and request.exists():
  change=json.loads(request.read_text());target=change.get('publish_date') or target
 due=slot_for(created,os.environ['GITHUB_EVENT_NAME'],event.get('schedule',''),target)
 if due is None:return {'run':False,'reason':'other DST trigger'}
 due=due.isoformat().replace('+00:00','Z');mapping=destinations(profile);queues={k:queued(v,due) for k,v in mapping.items()}
 if any(queues.values()):
  if not all(len(rows)==1 for rows in queues.values()):raise ValueError('Partial or ambiguous occupied slot; reconcile existing receipts, never submit duplicates')
  return {'run':False,'reason':'all three existing destination slots occupied; preserve them','due_at':due}
 selected=None
 def choose(data):
  nonlocal selected
  rows=[(k,e) for k,e in data['episodes'].items() if e.get('due_at') and instant(e['due_at'])==instant(due)]
  # A rejected creative candidate is retained, but never becomes the daily film.
  rows=[(k,e) for k,e in rows if not e.get('creative_rejected')]
  if len(rows)>1:raise ValueError('Multiple reserved films for one day need explicit reconciliation')
  if rows:selected={'slot':rows[0][0],**rows[0][1]}
  else:
   slot='daily-remotion-'+due[:10]+'-'+profile
   data['episodes'][slot]={'profile':profile,'due_at':due,'status':'author_pending','source_run':int(os.environ['GITHUB_RUN_ID']),'created_at':datetime.now(timezone.utc).isoformat()};selected={'slot':slot,**data['episodes'][slot]}
 if not args.dry_run:mutate(choose)
 return {'run':not args.dry_run,'reason':'eligible' if not args.dry_run else 'dry run; no provider mutation','profile':profile,'due_at':due,'entry':selected}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');parser.add_argument('--date');parser.add_argument('--decide-only',action='store_true');args=parser.parse_args();decision=decide(args)
 Path('professional_motion/output').mkdir(parents=True,exist_ok=True);Path('professional_motion/output/daily-decision.json').write_text(json.dumps(decision,ensure_ascii=False,indent=2))
 print(json.dumps(decision,ensure_ascii=False))
 if os.getenv('GITHUB_OUTPUT'):
  with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('run='+str(decision['run']).lower()+'\n')
 if not decision['run'] or args.decide_only:return
 entry=decision['entry'];profile=decision['profile'];req={'slot':entry['slot'],'profile':profile,'due_at':decision['due_at']};Path('.work').mkdir(exist_ok=True)
 request=Path('.work/remotion-request.json');request.write_text(json.dumps(req));os.environ['FACTORY_REQUEST_PATH']=str(request)
 ROOT.mkdir(parents=True,exist_ok=True)
 if entry['status'] in ('rendered','approved','publishing'):
  extract(entry['render_run'],'remotion-complete-',Path('completed'))
  movies=list(Path('completed').rglob('remotion-complete.mp4'))
  if len(movies)!=1:raise ValueError('Expected one exact completed film')
  movie=movies[0];report=json.loads((movie.parent/'remotion-validation.json').read_text())
  if hashlib.sha256(movie.read_bytes()).hexdigest()!=entry['video_sha256']:raise ValueError('Retained film differs from durable media fingerprint')
 else:
  from .author import author
  episode=author(req,entry);episode_path=Path('.work/episode.json');episode_path.write_text(json.dumps(episode,ensure_ascii=False,indent=2)+'\n');os.environ['REMOTION_EPISODE_PATH']=str(episode_path)
  from .prepare import main as prepare
  prepare()
  from .voice_job import main as voice
  voice()
  from .assets import main as assets
  assets();command('node','remotion_motion/render.mjs','--stills');command('node','remotion_motion/render.mjs')
  from .finish import main as finish
  finish();movie=Path('professional_motion/output/remotion-complete.mp4');report=json.loads((movie.parent/'remotion-validation.json').read_text())
  os.environ['REMOTION_COMPLETED_DIR']='professional_motion'
 # Approval is the owner's standing authorization of this renderer and workflow,
 # never a claim that the owner watched an automatically produced episode.
 from .quality import verify
 verify(movie,report,profile)
 approval=Path('.work/approval.json');approval.write_text(json.dumps({'video_sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'visual_review_passed':True,'approval_basis':'standing owner style approval plus automated scene/technical/source checks','owner_watched_this_episode':False}));os.environ['REMOTION_APPROVAL_PATH']=str(approval)
 from .publish import main as publish
 publish()
 from .cutover import main as cutover
 cutover()
if __name__=='__main__':main()
