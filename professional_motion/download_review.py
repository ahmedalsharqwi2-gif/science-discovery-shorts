"""Export verified Actions review artifacts to a download-only Git branch."""
import hashlib,io,json,os,subprocess,time,zipfile
from pathlib import Path
import requests
repo=os.environ['GITHUB_REPOSITORY'];profile=os.environ['REVIEW_PROFILE'];workflow=os.environ['REVIEW_WORKFLOW']
headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}
def api(path):
 r=requests.get('https://api.github.com/repos/'+repo+'/'+path,headers=headers,timeout=60)
 if r.status_code!=200:raise RuntimeError('Actions API returned HTTP '+str(r.status_code))
 return r.json()
run=None
for attempt in range(60):
 rows=api('actions/runs?branch=codex/daily-professional-factory&per_page=40')['workflow_runs']
 rows=[r for r in rows if r.get('path','').split('@')[0]=='.github/workflows/'+workflow]
 if rows:
  run=max(rows,key=lambda r:r['id'])
  if run['status']=='completed':
   if run['conclusion']!='success':raise RuntimeError('Latest professional review did not finish successfully; run '+str(run['id']))
   break
 time.sleep(20)
else:raise RuntimeError('Review still running; export can be retried without generating media again')
assets=api('actions/runs/'+str(run['id'])+'/artifacts')['artifacts'];artifact=next((a for a in assets if a['name'].startswith(profile+'-professional-') and not a['expired']),None)
if not artifact:raise RuntimeError('No current professional review artifact')
r=requests.get(artifact['archive_download_url'],headers=headers,timeout=180)
if r.status_code!=200:raise RuntimeError('Artifact download returned HTTP '+str(r.status_code))
root=Path('review_download');root.mkdir(exist_ok=True)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
 def find(suffix):
  rows=[n for n in z.namelist() if n.endswith(suffix)]
  if len(rows)!=1:raise ValueError('Missing or ambiguous review artifact entry: '+suffix)
  return z.read(rows[0])
 video=find('output/professional-review.mp4');verify=json.loads(find('output/verification.json'))
 if verify.get('profile')!=profile or verify.get('visual_gate',{}).get('passed') is not True or verify.get('audio_tail',{}).get('audio_tail_checked') is not True:raise ValueError('Artifact did not pass profile/media verification')
 (root/'review-1080p.mp4').write_bytes(video);(root/'verification.json').write_text(json.dumps(verify,ensure_ascii=False,indent=2))
subprocess.run(['ffmpeg','-v','error','-i',str(root/'review-1080p.mp4'),'-f','null','-'],check=True)
subprocess.run(['ffmpeg','-v','error','-y','-i',str(root/'review-1080p.mp4'),'-vf','scale=720:1280','-c:v','libx264','-preset','fast','-crf','24','-c:a','aac','-b:a','160k','-movflags','+faststart',str(root/'review-720p.mp4')],check=True)
branch='codex/professional-video-'+str(run['id']);base='https://github.com/'+repo+'/raw/refs/heads/'+branch+'/'
(root/'README.md').write_text('# Professional '+profile+' review\n\n[Download 720p]('+base+'review-720p.mp4)\n\n[Download original 1080p]('+base+'review-1080p.mp4)\n\nGenerated inside GitHub Actions. Review only; not social publication.\n')
def git(*args,data=None):return subprocess.check_output(['git',*args],input=data).decode().strip()
entries=[]
for p in root.iterdir():
 if p.name not in ['review-1080p.mp4','review-720p.mp4','verification.json','README.md']:continue
 blob=git('hash-object','-w',str(p));entries.append(f'100644 blob {blob}\t{p.name}\n')
tree=git('mktree',data=''.join(entries).encode());commit=git('-c','user.name=review-delivery-bot','-c','user.email=bot@users.noreply.github.com','commit-tree',tree,'-m','Deliver verified '+profile+' review downloads [skip ci]')
git('push','origin',commit+':refs/heads/'+branch)
print('Delivered',branch)
