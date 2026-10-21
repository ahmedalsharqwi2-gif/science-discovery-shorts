"""Publish complete verified films, retaining partial receipts for safe retries."""
import argparse,json,os,re,shutil
from pathlib import Path
import requests
from film_factory.metadata import create,BRANDS
from film_factory.buffer import ContentPublisher
from film_factory.delivery import probe
from scripts.publication_state import accepted_receipt,require_services,confirm_stock

def norm(value):
 return re.sub(r'[^a-z0-9\u0621-\u064a]','',str(value).lower()).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))
def query(text):
 key=os.getenv('BUFFER_API_KEY','').strip()
 if not key:raise ValueError('Missing BUFFER_API_KEY')
 r=requests.post('https://api.buffer.com',headers={'Authorization':'Bearer '+key},json={'query':text},timeout=45);r.raise_for_status();d=r.json()
 if d.get('errors'):raise RuntimeError('Buffer could not read organization/channel configuration')
 return d['data']
def channels(profile):
 services=('tiktok','youtube','facebook') if profile=='science' else ('youtube','facebook','instagram','tiktok')
 explicit={s:os.getenv('BUFFER_'+s.upper()+'_CHANNEL_ID','').strip() for s in services};explicit={k:v for k,v in explicit.items() if v}
 raw=os.getenv('BUFFER_CHANNEL_IDS','').strip()
 if raw:explicit.update(ContentPublisher._channel_map(raw,services))
 if explicit:return explicit
 # New repository: resolve ONLY uniquely matching brand names; never use an arbitrary channel.
 orgs=query('query { account { organizations { id name } } }')['account']['organizations'];found={};available=[]
 for org in orgs:
  rows=query('query { channels(input: {organizationId: '+json.dumps(org['id'])+'}) { id name displayName service isQueuePaused } }')['channels']
  for row in rows:
   available.append({'name':row.get('displayName') or row.get('name'),'service':row['service']})
   names=[norm(row.get('displayName','')),norm(row.get('name',''))];brand=norm(BRANDS[profile])
   if not any(brand and brand in name for name in names):continue
   service=row['service'].lower()
   if service in found:raise ValueError('More than one matching brand channel for '+service+'; configure explicit ID')
   if row.get('isQueuePaused'):raise ValueError('Matching Buffer queue is paused; unpause it before publication')
   found[service]=row['id']
 Path('output').mkdir(exist_ok=True);Path('output/channel-discovery.json').write_text(json.dumps({'matched_services':list(found),'available_channels':available},ensure_ascii=False,indent=2))
 print('Brand channel discovery:',json.dumps({'matched':list(found),'available':available},ensure_ascii=False),flush=True)
 if not found:raise ValueError('No uniquely matching '+BRANDS[profile]+' Buffer channel; configure BUFFER_CHANNEL_IDS or connect the intended page')
 return found
def preflight(profile):
 mapping=channels(profile)
 direct=all(os.getenv(k,'').strip() for k in ('YT_CLIENT_ID','YT_CLIENT_SECRET')) and bool(os.getenv('YT_REFRESH_TOKEN') or os.getenv('YT_REFRESH_TOKEN_FALLBACK'))
 if direct:mapping.pop('youtube',None)
 if not mapping and not direct:raise ValueError('No publication destinations are configured')
 p=Path('state/film_destinations.json');p.parent.mkdir(exist_ok=True);p.write_text(json.dumps({'buffer':mapping,'direct_youtube':direct},indent=2))
 print('Configured destinations:',', '.join(mapping)+(', direct YouTube' if direct else ''),flush=True)
 return mapping,direct
def main():
 parser=argparse.ArgumentParser();parser.add_argument('profile',choices=list(BRANDS));parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
 policy=Path('config/quality_release.json')
 if policy.exists() and json.loads(policy.read_text()).get('publication_approved') is not True:raise ValueError('Publication paused: visual and sound quality rejected; a new sample needs approval')
 mapping,direct=preflight(args.profile)
 if args.preflight:return
 out=Path('output');plan=json.loads((out/'plan.json').read_text());report=json.loads((out/'verification.json').read_text())
 if report.get('audio',{}).get('audio_tail_checked') is not True:raise ValueError('Complete narration tail verification is required')
 metadata=create(plan,args.profile)
 final=out/'final_video_full.mp4'
 if not final.exists():
  original=out/('ai-news-daily.mp4' if args.profile=='news' else args.profile+'-photo-charon.mp4');shutil.copyfile(original,final)
 streams=probe(final)['streams'];v=next(x for x in streams if x['codec_type']=='video');a=next(x for x in streams if x['codec_type']=='audio')
 if (v['width'],v['height'])!=(1080,1920) or a['channels']!=2:raise ValueError('Final publication requires 1080x1920 and verified stereo sound')
 Path('state/current_episode.json').write_text(json.dumps({**plan,**metadata},ensure_ascii=False,indent=2))
 required=set(mapping)|({'youtube'} if direct else set());require_services(required)
 failures=[]
 if mapping:
  os.environ['BUFFER_CHANNEL_IDS']=','.join(k+':'+v for k,v in mapping.items());os.environ['PUBLISH_CHANNELS']=','.join(mapping)
  try:
   if not ContentPublisher().publish_to_buffer(final,metadata['title'],metadata['caption'],[]):failures.append('Buffer did not accept every configured channel')
  except Exception as exc:failures.append('Buffer: '+str(exc))
 if direct:
  from scripts.publish_youtube_direct import main as youtube
  if youtube()!=0:failures.append('Direct YouTube publication failed')
 if failures:raise RuntimeError('; '.join(failures))
 os.environ['BUFFER_OUTCOME']='success'
 if direct:os.environ['YOUTUBE_OUTCOME']='success'
 confirm_stock()
 (out/'publication-result.json').write_text(json.dumps({'provider_acceptance_confirmed':True,'services':sorted(required),'receipts':{s:accepted_receipt(s) for s in required},'social_delivery_still_subject_to_platform_processing':True},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
