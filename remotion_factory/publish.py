"""Schedule an approved complete film once, with durable pre-submit intents."""
import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
import requests
from .prepare import read_request
from .state import identity,mutate
from .audio_delivery import probe
from .packaging import video_asset,verify as verify_publication
def instant(value):return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
def query(text,variables=None):
 r=requests.post('https://api.buffer.com',headers={'Authorization':'Bearer '+os.environ['BUFFER_API_KEY'].strip()},json={'query':text,**({'variables':variables} if variables else {})},timeout=60)
 if r.status_code!=200:raise RuntimeError('Buffer HTTP request failed; reconcile retained intent before retry')
 data=r.json()
 if data.get('errors'):raise RuntimeError('Buffer query rejected; provider details and credentials omitted')
 return data['data']
FIELDS='id channelId status dueAt assets {source}'
class DestinationUnavailable(ValueError):pass
def lookup(identifier):return query('query {post(input:{id:'+json.dumps(identifier)+'}) {'+FIELDS+'}}')['post']
def matches(post,channel,due,url):return post.get('channelId')==channel and post.get('status')=='scheduled' and instant(post['dueAt'])==instant(due) and url in [a.get('source') for a in post.get('assets',[])]
def destinations(profile):
 cfg=json.loads(Path('config/professional_destinations.json').read_text());mapping=cfg.get('buffer_channel_ids',{})
 if cfg.get('profile')!=profile or cfg.get('existing_bindings_confirmed_by_user') is not True or len(mapping)!=3 or len(set(mapping.values()))!=3:raise ValueError('Exactly three confirmed own-repository destinations required')
 selected={}
 for org in query('query {account {organizations {id}}}')['account']['organizations']:
  rows=query('query {channels(input:{organizationId:'+json.dumps(org['id'])+'}) {id service isQueuePaused isDisconnected}}')['channels']
  for row in rows:
   service=row['service'].lower()
   if mapping.get(service)==row['id']:
    if row.get('isQueuePaused') is not False:raise DestinationUnavailable(service+': confirmed destination queue is paused')
    if row.get('isDisconnected') is not False:raise DestinationUnavailable(service+': Buffer channel connection is unavailable; refresh this channel in Buffer before production')
    selected[service]={'channel':row['id'],'organization':org['id']}
 if set(selected)!=set(mapping):raise ValueError('A confirmed repository destination is missing or has another service')
 return selected
def queued(destination,due,include_errors=False):
 start=(instant(due)-timedelta(seconds=1)).isoformat();end=(instant(due)+timedelta(seconds=1)).isoformat();rows=[];cursor=None
 for _ in range(20):
  after=',after:'+json.dumps(cursor) if cursor else ''
  statuses='scheduled,sending,sent,error' if include_errors else 'scheduled,sending,sent'
  data=query('query {posts(first:100'+after+',input:{organizationId:'+json.dumps(destination['organization'])+',filter:{channelIds:['+json.dumps(destination['channel'])+'],dueAt:{start:'+json.dumps(start)+',end:'+json.dumps(end)+'},status:['+statuses+']}}){edges{node{'+FIELDS+'}} pageInfo{hasNextPage endCursor}}}')['posts']
  rows.extend(e['node'] for e in data.get('edges') or [])
  if not data['pageInfo']['hasNextPage']:return rows
  cursor=data['pageInfo']['endCursor']
 raise ValueError('Queue inspection could not complete within its bound')
def release_asset(movie,slot,profile):
 repo,_=identity();token=os.environ['GITHUB_TOKEN'];headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json'};base=f'https://api.github.com/repos/{repo}';tag='production-'+slot
 r=requests.get(base+'/releases/tags/'+tag,headers=headers,timeout=30)
 if r.status_code==404:
  r=requests.post(base+'/releases',headers=headers,json={'tag_name':tag,'name':'Complete '+profile+' production '+slot,'body':'Complete original-narration production. Source and media fingerprints are retained in state/remotion_registry.json.','draft':False,'prerelease':False},timeout=30)
 r.raise_for_status();release=r.json();name=profile+'-'+slot+'.mp4';digest=hashlib.sha256(movie.read_bytes()).hexdigest()
 old=next((a for a in release.get('assets',[]) if a['name']==name),None)
 if old:
  if old.get('digest')!='sha256:'+digest:raise ValueError('Existing production release bytes differ; never overwrite or reuse another film')
  return old['browser_download_url']
 upload=release['upload_url'].split('{',1)[0]
 with movie.open('rb') as content:r=requests.post(upload,params={'name':name},headers={**headers,'Content-Type':'video/mp4'},data=content,timeout=180)
 r.raise_for_status();asset=r.json()
 if asset.get('digest')!='sha256:'+digest:raise ValueError('Uploaded production fingerprint was not independently confirmed')
 return asset['browser_download_url']
def submit_one(service,destination,due,url,title,caption,record,persist,publication=None):
 channel=destination['channel']
 if not record.get('id'):
  rows=queued(destination,due);same=[p for p in rows if matches(p,channel,due,url)]
  if len(same)==1:record.update(id=same[0]['id'],phase='reconciled');persist()
  elif rows:raise ValueError('Another post already occupies this exact destination/time; no duplicate submission')
  elif record.get('phase') in ('intent','uncertain'):raise ValueError('Previous submission is unacknowledged; reconciliation is required, not another send')
  else:
   record.update(phase='intent',channel_id=channel,due_at=due,media_url=url,created_at=datetime.now(timezone.utc).isoformat());persist()
   payload={'channelId':channel,'text':caption[:2200] if service=='tiktok' else caption,'mode':'customScheduled','schedulingType':'automatic','dueAt':due,'assets':[video_asset(url,service,publication)]}
   metadata={'youtube':{'title':title[:100],'categoryId':'27','privacy':'public','madeForKids':False,'notifySubscribers':False},'facebook':{'type':'post'},'instagram':{'type':'reel','shouldShareToFeed':True}}
   if service in metadata:payload['metadata']={service:metadata[service]}
   try:
    result=query('mutation ScheduleCompleteRemotion($input:CreatePostInput!){createPost(input:$input){... on PostActionSuccess{post{id dueAt}} ... on MutationError{message}}}',{'input':payload})['createPost']
    identifier=result.get('post',{}).get('id')
    if not identifier:raise RuntimeError('Provider did not acknowledge a post ID')
    record.update(id=identifier,phase='acknowledged',accepted_at=datetime.now(timezone.utc).isoformat());persist()
   except Exception:record['phase']='uncertain';persist();raise
 actual=lookup(record['id'])
 if actual.get('id')!=record['id'] or not matches(actual,channel,due,url):raise ValueError('Independent same-ID scheduled-state verification failed')
 record.update(phase='verified',status='scheduled',scheduled_at=actual['dueAt'],verified_at=datetime.now(timezone.utc).isoformat());persist()
def main():
 req=read_request();repo,profile=identity();approval=json.loads(Path(os.getenv('REMOTION_APPROVAL_PATH','.github/remotion-publish-request.json')).read_text());root=Path(os.getenv('REMOTION_COMPLETED_DIR','completed'))
 movies=list(root.glob('**/remotion-complete.mp4'))
 if len(movies)!=1:raise ValueError('Exactly one full retained movie required')
 movie=movies[0];report=json.loads((movie.parent/'remotion-validation.json').read_text());digest=hashlib.sha256(movie.read_bytes()).hexdigest()
 if approval.get('video_sha256')!=digest or report.get('video_sha256')!=digest or report.get('profile')!=profile or report.get('review_sample') or report.get('fully_decoded') is not True:raise ValueError('Full reviewed media proof does not match this exact file')
 if approval.get('visual_review_passed') is not True:raise ValueError('Actual full-film visual review is missing')
 if profile=='news':
  published=report.get('source',{}).get('published')
  if not published or not timedelta(0)<=instant(req['due_at'])-instant(published)<=timedelta(hours=72):raise ValueError('News must still be fresh at actual publication time')
 meta=probe(movie);duration=float(meta['format']['duration']);minimum=60 if profile=='news' else 90
 if not minimum<duration<180:raise ValueError('Actual movie fails the permanent owner duration rule')
 publication=verify_publication(movie.parent,report)
 mapping=destinations(profile);due=req['due_at'];entry=None
 def check(data):
  nonlocal entry
  entry=data['episodes'][req['slot']]
  if entry.get('video_sha256')!=digest:raise ValueError('Ledger media differs from the reviewed film')
 mutate(check)
 url=entry.get('media_url') or release_asset(movie,req['slot'],profile)
 def media(data):data['episodes'][req['slot']].update(media_url=url,status='publishing')
 mutate(media)
 source=report['source'];story_path=next((p for p in root.glob('**/story.json') if hashlib.sha256(p.read_bytes()).hexdigest()==report.get('story_sha256')),None);story=json.loads(story_path.read_text()) if story_path else {};title=report.get('title') or story.get('title') or entry['title'];title=publication['title'] if publication else title;caption=title
 tags=['#'+str(t).lstrip('#').strip().replace(' ','_') for t in story.get('hashtags',[])[:5]]
 if tags:caption+='\n'+' '.join(tags)
 if source.get('url'):caption+='\nالمصدر: '+source['url']
 credits=report.get('licensed_assets',{}).get('assets',[])
 if credits:
  from .asset_credits import format_credits
  caption+='\nاعتمادات الصور:\n'+format_credits(credits)
 for service,destination in mapping.items():
  record=dict(entry.get('receipts',{}).get(service,{}))
  def persist():
   def update(data):
    e=data['episodes'][req['slot']];old=e.setdefault('receipts',{}).get(service,{})
    if old.get('id') and record.get('id')!=old['id']:raise ValueError('Accepted provider ID cannot be replaced')
    e['receipts'][service]=dict(record)
   mutate(update)
  submit_one(service,destination,due,url,title,caption,record,persist,publication)
 def done(data):
  e=data['episodes'][req['slot']]
  if len(e.get('receipts',{}))!=3 or not all(r.get('phase')=='verified' and r.get('id') for r in e['receipts'].values()):raise ValueError('Three independently verified receipts required')
  e.update(status='scheduled',due_at=due)
 mutate(done);print(json.dumps({'status':'scheduled','profile':profile,'due_at':due,'media_url':url,'receipts_verified':3}))
if __name__=='__main__':main()

