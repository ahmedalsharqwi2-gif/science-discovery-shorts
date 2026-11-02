import hashlib,io,json,os,zipfile
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from .state import identity,mutate
DELIVERY=Path('professional_motion/delivery')
def read_request():
 req=json.loads(Path('.github/remotion-request.json').read_text());_,profile=identity()
 if req['profile']!=profile:raise ValueError('Request belongs to a different channel')
 due=datetime.fromisoformat(req['due_at'].replace('Z','+00:00'))
 if due<=datetime.now(timezone.utc) or due.astimezone(ZoneInfo('Africa/Cairo')).strftime('%H:%M:%S')!='17:00:00':raise ValueError('Publication slot invalid or expired; never roll it forward')
 return req
def restore(entry,story_hash):
 run=entry['source_run'];repo,_=identity();h={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'}
 r=requests.get(f'https://api.github.com/repos/{repo}/actions/runs/{run}/artifacts',headers=h,timeout=30);r.raise_for_status()
 matches=[a for a in r.json()['artifacts'] if not a['expired'] and a['name'].startswith(f'remotion-voice-{run}-')]
 if not matches:raise RuntimeError('Prior voice request retained but no recoverable artifact; refusing repeated synthesis')
 a=max(matches,key=lambda x:x['id']);r=requests.get(a['archive_download_url'],headers=h,timeout=90);r.raise_for_status()
 if len(r.content)>150_000_000:raise ValueError('Retained voice artifact exceeds bounds')
 with zipfile.ZipFile(io.BytesIO(r.content)) as z:
  files={i.filename:z.read(i) for i in z.infolist() if not i.is_dir() and len(Path(i.filename).parts)==1 and Path(i.filename).suffix in ('.json','.wav')}
 if hashlib.sha256(files.get('story.json',b'')).hexdigest()!=story_hash or 'narration.wav' not in files:raise ValueError('Prior voice artifact does not contain this exact story and voice')
 for name,content in files.items():(DELIVERY/name).write_bytes(content)
def main():
 req=read_request();story=json.loads(Path('config/remotion_episode.json').read_text());_,profile=identity()
 if story['profile']!=profile or len(story['scenes'])!=8:raise ValueError('Eight authored scenes for this profile required')
 if profile in ('history','horror') and (story.get('fiction') or not story.get('documented') or not story.get('source',{}).get('url')):raise ValueError('History and horror must be sourced true events; invented stories are forbidden')
 raw=(json.dumps(story,ensure_ascii=False,indent=2)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();old=None
 def reserve(data):
  nonlocal old
  episodes=data['episodes'];old=episodes.get(req['slot'])
  if old:
   if old['story_sha256']!=digest:raise ValueError('Reserved narration cannot silently change')
   if old['status']=='scheduled':raise RuntimeError('Slot already scheduled; no duplicate generation or sending')
   return
  if any(e['canonical_subject']==story['canonical_subject'] for e in episodes.values()):raise ValueError('Underlying subject already reserved')
  for name in ('state/professional_topics.json','state/film_topics.json','state/topic_history.json'):
   path=Path(name)
   if not path.exists():continue
   prior=json.loads(path.read_text());rows=prior if isinstance(prior,list) else prior.get('episodes',prior.get('produced',prior.get('entries',[])))
   if any(isinstance(e,dict) and (e.get('canonical_subject')==story['canonical_subject'] or e.get('topic_key')==story['topic_key']) for e in rows):raise ValueError('Subject conflicts with retained legacy history')
  episodes[req['slot']]={'status':'reserved','canonical_subject':story['canonical_subject'],'title':story['title'],'story_sha256':digest,'due_at':req['due_at'],'profile':profile,'source_run':int(os.environ['GITHUB_RUN_ID']),'created_at':datetime.now(timezone.utc).isoformat()}
 mutate(reserve);DELIVERY.mkdir(parents=True,exist_ok=True)
 if old and old['status'] in ('voice_requested','voice_ready','rendered','approved'):restore(old,digest)
 (DELIVERY/'story.json').write_bytes(raw)
 print(json.dumps({'profile':profile,'slot':req['slot'],'retained_voice_restored':bool(old),'spoken_words':sum(len(s['narration'].split()) for s in story['scenes'])}))
if __name__=='__main__':main()
