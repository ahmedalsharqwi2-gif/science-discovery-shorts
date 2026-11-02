"""Read-only production/social audit. Never writes topics, synthesizes or publishes."""
import argparse,base64,hashlib,json,math,os,re,statistics,subprocess,sys,tempfile
from datetime import datetime,time,timedelta,timezone
from pathlib import Path
from urllib.parse import unquote,urlparse
from zoneinfo import ZoneInfo
import requests
from .state import identity
from .publish import destinations,queued,query,instant
CAIRO=ZoneInfo('Africa/Cairo')
CHECKPOINTS=((11,30),(15,0),(16,15),(17,30))
MARKER='<!-- remotion-daily-health -->'
class AuditFailure(Exception):pass
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def schedule_allowed(created,cron):
 local=created.astimezone(CAIRO);offset=int(local.utcoffset().total_seconds()/3600)
 for hour,minute in CHECKPOINTS:
  nominal=local.replace(hour=hour,minute=minute,second=0,microsecond=0)
  if cron==f'{minute} {hour-offset} * * *' and nominal<=local<=nominal+timedelta(minutes=90):return True
 return False
def gh(path,method='GET',payload=None,raw=False):
 repo,_=identity();headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github.raw+json' if raw else 'application/vnd.github+json'}
 r=requests.request(method,'https://api.github.com/repos/'+repo+path,headers=headers,json=payload,timeout=45)
 if r.status_code==404 and method=='GET':return None
 if not 200<=r.status_code<300:raise AuditFailure('GitHub audit API unavailable: HTTP'+str(r.status_code))
 if raw:return r.text
 return r.json() if r.content else {}
def read_json(path,default=None):
 p=Path(path)
 if not p.exists():return default
 return json.loads(p.read_text())
def write_json(path,data):
 content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
 if os.getenv('GITHUB_ACTIONS')=='true':
  for attempt in range(3):
   old=gh('/contents/'+path+'?ref=main');payload={'message':'Record independent daily video health evidence [skip ci]','branch':'main','content':base64.b64encode(content.encode()).decode()}
   if old:payload['sha']=old['sha']
   try:gh('/contents/'+path,'PUT',payload);break
   except AuditFailure:
    if attempt==2:raise
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
def target_due(day):return datetime.combine(day,time(17),CAIRO).astimezone(timezone.utc)
def check_posts(mapping,rows,due,phase):
 selected={};media=set();ids=set()
 for service,destination in mapping.items():
  posts=rows.get(service,[])
  if len(posts)!=1:raise AuditFailure(service+': missing post or duplicate posts at17Cairo')
  post=posts[0]
  if not post.get('id') or post['id'] in ids or post.get('channelId')!=destination['channel']:raise AuditFailure(service+': post identity/channel mismatch')
  ids.add(post['id'])
  if not post.get('dueAt') or abs((instant(post['dueAt'])-due).total_seconds())>1:raise AuditFailure(service+': publication time differs from17Cairo')
  if phase=='postpublish':
   if post.get('status')!='sent' or not post.get('sentAt') or not post.get('externalLink'):raise AuditFailure(service+': Buffer has not confirmed sent publication with an external link')
  elif post.get('status')!='scheduled':raise AuditFailure(service+': post is not scheduled')
  urls=[a.get('source') for a in post.get('assets',[]) if a.get('source')]
  if len(urls)!=1:raise AuditFailure(service+': exactly one complete video source required')
  media.add(urls[0]);selected[service]={k:post.get(k) for k in ('id','channelId','status','dueAt','sentAt','externalLink')}
 if len(selected)!=3 or len(media)!=1:raise AuditFailure('Three own destinations must reference the same film')
 return selected,media.pop()
def episode_for(day,url):
 candidates=[]
 remotion=read_json('state/remotion_registry.json',{'episodes':{}})
 for slot,e in remotion.get('episodes',{}).items():candidates.append(dict(e,slot=slot,pipeline='remotion'))
 legacy=read_json('state/professional_topics.json',{'episodes':[]})
 rows=legacy if isinstance(legacy,list) else legacy.get('episodes',[])
 if isinstance(rows,dict):rows=list(rows.values())
 candidates.extend(dict(e,pipeline='legacy') for e in rows)
 stickman=read_json('state/stickman_publications.json',{})
 for key in ('publications','episodes'):
  values=stickman.get(key,{})
  if isinstance(values,dict):candidates.extend(dict(e,slot=slot,pipeline='legacy-stickman') for slot,e in values.items())
  elif isinstance(values,list):candidates.extend(dict(e,pipeline='legacy-stickman') for e in values)
 result=[]
 for e in candidates:
  if e.get('creative_rejected'):continue
  due=e.get('due_at')
  if not due or instant(due).astimezone(CAIRO).date()!=day:continue
  urls={e.get('media_url')}
  for r in (e.get('receipts') or e.get('posts') or {}).values():
   if isinstance(r,dict):urls.add(r.get('media_url'))
  # Older ledgers omit media_url. The immutable release digest must then prove the binding.
  if url not in urls and any(u for u in urls):continue
  digest=e.get('publication_video_sha256') or e.get('video_sha256')
  if digest:result.append(dict(e,expected_sha256=digest))
 if len(result)!=1:raise AuditFailure('No unique retained episode/media fingerprint for this date and actual post video')
 return result[0]
def release_for(url):
 repo,_=identity();prefix='https://github.com/'+repo+'/releases/download/'
 if not url.startswith(prefix):raise AuditFailure('Video is not an immutable release of this own repository')
 parts=url[len(prefix):].split('/')
 if len(parts)!=2:raise AuditFailure('Invalid own-release video path')
 tag,name=map(unquote,parts);release=gh('/releases/tags/'+requests.utils.quote(tag,safe=''))
 if not release or release.get('draft'):raise AuditFailure('Production video release is missing or inaccessible')
 rows=[a for a in release.get('assets',[]) if a.get('name')==name and a.get('browser_download_url')==url and a.get('state')=='uploaded']
 if len(rows)!=1:raise AuditFailure('Exact full-video release asset missing')
 return rows[0]
def technical(movie,expected,profile):
 if sha(movie)!=expected:raise AuditFailure('Downloaded full-video fingerprint differs from retained production')
 p=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)],capture_output=True,text=True,check=True);meta=json.loads(p.stdout)
 videos=[s for s in meta['streams'] if s['codec_type']=='video'];audios=[s for s in meta['streams'] if s['codec_type']=='audio'];duration=float(meta['format']['duration'])
 if len(videos)!=1 or not audios or (videos[0]['width'],videos[0]['height'])!=(1080,1920):raise AuditFailure('Full1080x1920 video and real audio stream required')
 if not (60 if profile=='news' else 90)<duration<180:raise AuditFailure('Permanent measured-duration rule failed')
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],capture_output=True,check=True)
 audio=subprocess.run(['ffmpeg','-hide_banner','-i',str(movie),'-vn','-af','volumedetect','-f','null','-'],capture_output=True,text=True,check=True)
 volume=re.search(r'mean_volume:\s*(-?[\d.]+) dB',audio.stderr)
 if not volume or float(volume.group(1))< -45:raise AuditFailure('Missing or nearly silent audio')
 frames=subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf',f'fps=12/{duration},scale=160:284,format=gray','-frames:v','12','-f','rawvideo','-'],capture_output=True,check=True).stdout
 size=160*284;shots=[frames[i:i+size] for i in range(0,len(frames),size) if len(frames[i:i+size])==size]
 if len(shots)<10 or any(statistics.pstdev(s)<5 for s in shots):raise AuditFailure('Blank frames or insufficient full-film visual samples')
 unique=len({hashlib.sha256(s).hexdigest() for s in shots})
 if unique<6:raise AuditFailure('Frozen/repeated visual sequence')
 return {'passed':True,'sha256':expected,'full_decode':True,'duration':duration,'width':1080,'height':1920,'audio_mean_db':float(volume.group(1)),'actual_visual_samples':len(shots),'unique_visual_samples':unique,'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'Independent technical media check; no claim of human narrative or scientific review'}
def verify_media(url,episode,profile):
 asset=release_for(url);expected=episode['expected_sha256'];digest=asset.get('digest')
 if digest and digest!='sha256:'+expected:raise AuditFailure('Live release digest changed after production')
 cache_path='reviews/daily_health/media/'+expected+'.json';cache=read_json(cache_path,{})
 signature={k:asset.get(k) for k in ('id','size','updated_at','digest')}
 if cache.get('asset')==signature and cache.get('technical',{}).get('sha256')==expected and cache['technical'].get('passed'):
  return {**cache['technical'],'reused_immutable_media_check':True,'live_asset_metadata_verified':True}
 if not 1000<asset.get('size',0)<=500_000_000:raise AuditFailure('Release media size outside audit bounds')
 with tempfile.TemporaryDirectory() as folder:
  movie=Path(folder)/'complete.mp4'
  with requests.get(url,stream=True,timeout=(20,120)) as response:
   response.raise_for_status();count=0
   with movie.open('wb') as f:
    for chunk in response.iter_content(1024*1024):
     count+=len(chunk)
     if count>500_000_000:raise AuditFailure('Video download exceeds bound')
     f.write(chunk)
  result=technical(movie,expected,profile)
 write_json(cache_path,{'asset':signature,'technical':result})
 return {**result,'reused_immutable_media_check':False,'live_asset_metadata_verified':True}
def scheduler(day):
 data=gh('/actions/workflows/remotion-daily.yml/runs?event=schedule&per_page=100&created='+day.isoformat()) or {}
 rows=[r for r in data.get('workflow_runs',[]) if instant(r['created_at']).astimezone(CAIRO).date()==day and 9<=instant(r['created_at']).astimezone(CAIRO).hour<13]
 expected=target_due(day)
 for run in rows:
  if run['status']!='completed' or run.get('conclusion')!='success':continue
  jobs=(gh('/actions/runs/'+str(run['id'])+'/jobs') or {}).get('jobs',[])
  for job in jobs:
   logs=gh('/actions/jobs/'+str(job['id'])+'/logs',raw=True) or ''
   for line in logs.splitlines():
    i=line.find('{"run":')
    if i<0:continue
    try:decision=json.loads(line[i:])
    except ValueError:continue
    if decision.get('due_at') and instant(decision['due_at'])==expected and decision.get('reason')!='other DST trigger':return {'observed':True,'run_id':run['id'],'run_url':run['html_url'],'conclusion':'success','decision_reason':decision.get('reason')}
 raise AuditFailure('No successful actual9am daily run for this date; production may not have started or completed')
def alert(report):
 title='Daily video health — '+report['date'];existing=None
 for page in range(1,4):
  rows=gh(f'/issues?state=all&per_page=100&page={page}') or []
  existing=next((r for r in rows if not r.get('pull_request') and r.get('title')==title and MARKER in (r.get('body') or '')),None)
  if existing or len(rows)<100:break
 if report['passed'] and not existing:return
 repo,_=identity();summary='✅ الفحص اليومي سليم' if report['passed'] else '🚨 فحص مصنع الفيديوهات يحتاج إصلاحًا'
 errors='\n'.join('- '+e for e in report['errors']) or '- الفيديو وإيصالات النشر متحقق منها.'
 body=MARKER+'\n'+summary+'\n\n'+errors+'\n\nالتاريخ: '+report['date']+' — المرحلة: '+report['phase']+'\n\n'+report['run_url']+'\n\nالتقرير: https://github.com/'+repo+'/blob/main/'+report['report_path']+'\n\nهذا الفحص لا يعيد التوليد أو الإرسال، ولا ينقل الموعد الفائت.'
 if existing:
  gh('/issues/'+str(existing['number']),'PATCH',{'state':'closed' if report['passed'] else 'open','body':body})
 elif not report['passed']:gh('/issues','POST',{'title':title,'body':body})
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--date');parser.add_argument('--phase',choices=['auto','prepublish','postpublish'],default='auto');args=parser.parse_args();repo,profile=identity();now=datetime.now(timezone.utc);event=read_json(os.environ.get('GITHUB_EVENT_PATH',''),{}) or {};created=instant((gh('/actions/runs/'+os.environ['GITHUB_RUN_ID']) or {})['created_at']);policy=read_json('config/remotion_health.json',{})
 if os.getenv('GITHUB_EVENT_NAME')=='schedule' and not schedule_allowed(created,event.get('schedule','')):print('Other DST checkpoint; no duplicate audit');return
 inputs=event.get('inputs',{})
 if os.getenv('GITHUB_EVENT_NAME')=='push':inputs=read_json('.github/remotion-health-request.json',{}) or {}
 raw_date=args.date or inputs.get('date');day=datetime.fromisoformat(raw_date).date() if raw_date else created.astimezone(CAIRO).date();due=target_due(day);phase=args.phase if args.phase!='auto' else inputs.get('phase','auto')
 if phase=='auto':phase='postpublish' if now>=due+timedelta(minutes=20) else 'prepublish'
 activation=instant(policy['activated_at_utc']);first_day=activation.astimezone(CAIRO).date()+timedelta(days=1)
 if not raw_date and (day<first_day or created.astimezone(CAIRO).hour<9):print('Monitoring starts at first morning after activation; no false historical alert');return
 run_url='https://github.com/'+repo+'/actions/runs/'+os.environ['GITHUB_RUN_ID'];path='reviews/daily_health/'+day.isoformat()+'/'+os.environ['GITHUB_RUN_ID']+'-'+os.environ.get('GITHUB_RUN_ATTEMPT','1')+'.json'
 report={'date':day.isoformat(),'profile':profile,'phase':phase,'checked_at':now.isoformat(),'run_url':run_url,'report_path':path,'publication_due_utc':due.isoformat(),'errors':[],'passed':False,'generation_calls':0,'publication_mutations':0,'preview':day>now.astimezone(CAIRO).date()}
 if not report['preview'] and day>=first_day:
  try:report['scheduler']=scheduler(day)
  except Exception as exc:report['errors'].append(str(exc) if isinstance(exc,AuditFailure) else 'Scheduler verification unavailable: '+type(exc).__name__)
 else:report['scheduler']={'observed':False,'reason':'Future date preview; actual9am clock event not due yet'}
 try:
  mapping=destinations(profile);rows={}
  for service,destination in mapping.items():
   discovered=queued(destination,due.isoformat());rows[service]=[]
   for post in discovered:
    actual=query('query {post(input:{id:'+json.dumps(post['id'])+'}){id channelId status dueAt sentAt externalLink assets{source}}}')['post']
    rows[service].append(actual)
  report['receipts'],url=check_posts(mapping,rows,due,phase);episode=episode_for(day,url);report['episode']={k:episode.get(k) for k in ('slot','title','pipeline','expected_sha256')};report['technical']=verify_media(url,episode,profile)
 except Exception as exc:report['errors'].append(str(exc) if isinstance(exc,AuditFailure) else 'Live media/provider verification unavailable: '+type(exc).__name__)
 if os.getenv('GITHUB_EVENT_NAME')=='workflow_run' and event.get('workflow_run',{}).get('conclusion') not in ('success','skipped'):report['errors'].append('Production workflow failed/cancelled; inspect its retained evidence')
 report['passed']=not report['errors']
 try:write_json(path,report);write_json('reviews/daily_health/latest.json',report)
 except Exception as exc:report['passed']=False;report['errors'].append('Audit persistence failed: '+type(exc).__name__)
 Path('health-output').mkdir(exist_ok=True);Path('health-output/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 if os.getenv('GITHUB_STEP_SUMMARY'):
  with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write(('✅' if report['passed'] else '🚨')+' '+profile+' '+day.isoformat()+' '+phase+'\n\n'+('\n'.join('- '+e for e in report['errors']) or 'Full video and three live destination receipts verified.')+'\n')
 try:alert(report)
 except Exception as exc:
  report['errors'].append('GitHub issue alert unavailable: '+type(exc).__name__);report['passed']=False;Path('health-output/report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
  try:write_json(path,report);write_json('reviews/daily_health/latest.json',report)
  except Exception:pass
 print(json.dumps({'passed':report['passed'],'date':report['date'],'phase':phase,'errors':report['errors'],'generation_calls':0,'publication_mutations':0},ensure_ascii=False))
 if not report['passed']:sys.exit(1)
if __name__=='__main__':main()
