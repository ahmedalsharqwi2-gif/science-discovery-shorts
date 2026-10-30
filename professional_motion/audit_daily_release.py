"""Read-only proof of the current daily film's three real Buffer schedules."""
import json,sys
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .editorial import registry
from .publisher import confirmed_bindings
from film_factory.publish import query

def main(profile):
 local=datetime.now(ZoneInfo('Africa/Cairo'));slot='daily-'+local.date().isoformat();due=local.replace(hour=17,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
 episode=next(r for r in registry()['episodes'] if r.get('slot')==slot)
 if episode.get('status')!='scheduled':raise ValueError('Current daily film has not completed scheduling')
 mapping=confirmed_bindings(profile)
 if len(mapping)!=3 or set(episode.get('receipts',{}))!=set(mapping):raise ValueError('Missing one of the three required receipt destinations')
 expected=episode.get('media_correction',{}).get('media_url') or ('https://github.com/'+__import__('os').environ['GITHUB_REPOSITORY']+'/releases/download/auto-publish-'+slot+'/science-video-'+slot+'.mp4')
 result={'profile':profile,'slot':slot,'checked_at':datetime.now(timezone.utc).isoformat(),'video_sha256':episode['video_sha256'],'due_at':due.isoformat(),'no_posts_created':True,'verified':False,'posts':{}}
 out=Path('professional_motion/delivery');out.mkdir(exist_ok=True)
 for service,channel in mapping.items():
  receipt=episode['receipts'][service]
  actual=query('query { post(input:{id:'+json.dumps(receipt['id'])+'}) {id channelId status dueAt assets {source}} }')['post']
  sources=[a.get('source') for a in actual.get('assets',[])]
  if actual.get('id')!=receipt['id'] or actual.get('channelId')!=channel or actual.get('status')!='scheduled' or datetime.fromisoformat(actual['dueAt'].replace('Z','+00:00'))!=due or expected not in sources:raise ValueError('Actual Buffer post/channel/time/media do not match the current film')
  result['posts'][service]={'post_id':actual['id'],'channel_id':actual['channelId'],'scheduled_at':actual['dueAt'],'status':actual['status'],'media_url':expected}
 result['verified']=True;(out/'daily-publication-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main(sys.argv[1])
