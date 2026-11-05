"""Owner-authorized exact-file replacement; edits existing IDs only, never creates posts."""
import copy,hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
from remotion_factory.state import local,mutate
from remotion_factory.publish import query,instant,destinations,queued

FIELDS='id channelId channelService status dueAt text shareMode schedulingType assets {source} metadata {__typename ... on YoutubePostMetadata {title category {id} privacy license embeddable madeForKids notifySubscribers isAiGenerated annotations {__typename}} ... on FacebookPostMetadata {type title firstComment annotations {__typename} linkAttachment {__typename}} ... on InstagramPostMetadata {type shouldShareToFeed isAiGenerated link firstComment annotations {__typename} geolocation {__typename} stickerFields {__typename}} ... on TiktokPostMetadata {title isAiGenerated annotations {__typename}}}'
def lookup(identifier):
 return query('query {post(input:{id:'+json.dumps(identifier)+'}) {'+FIELDS+'}}')['post']
def payload(post,request):
 service=post['channelService'].lower();m=copy.deepcopy(post.get('metadata') or {})
 if any(m.get(k) for k in ('annotations','geolocation','stickerFields','linkAttachment')):raise ValueError('Complex existing metadata requires preservation, no partial edit')
 keys={'youtube':('title','privacy','license','embeddable','madeForKids','notifySubscribers','isAiGenerated'),'facebook':('type','firstComment'),'instagram':('type','shouldShareToFeed','isAiGenerated','link','firstComment'),'tiktok':('title','isAiGenerated')}
 values={k:m[k] for k in keys[service] if m.get(k) is not None}
 if service=='youtube':
  if not m.get('category',{}).get('id'):raise ValueError('Missing original YouTube category')
  values['categoryId']=str(m['category']['id'])
 if 'title' in values or service=='youtube':values['title']=request['story']['title']
 if values.get('firstComment'):values['firstComment']=request['hashtags']
 return {'id':post['id'],'dueAt':request['due_at'],'mode':'customScheduled','schedulingType':post['schedulingType'],'text':request['caption'],'assets':[{'video':{'url':request['new_media_url']}}],'metadata':{service:values}}
def verify(post,receipt,request,new=True):
 expected=request['new_media_url'] if new else request['old_media_url']
 if post.get('id')!=receipt['id'] or post.get('channelId')!=receipt['channel_id'] or post.get('status')!='scheduled' or instant(post['dueAt'])!=instant(request['due_at']) or [a['source'] for a in post.get('assets',[])]!=[expected]:raise ValueError('Exact ID/channel/time/media verification failed')
 if new and (post.get('text')!=request['caption'] or (post['channelService'].lower()=='youtube' and post.get('metadata',{}).get('title')!=request['story']['title'])):raise ValueError('Replacement caption/title not verified')
def main():
 request=json.loads(Path('.github/replace-noon-request.json').read_text());due=instant(request['due_at']);now=datetime.now(timezone.utc)
 if os.environ['GITHUB_REPOSITORY']!=request['repository'] or request['request_id']!='owner-replace-five-identity-films-2026-11-05' or request['due_at']!='2026-11-05T10:00:00Z' or now>=due:raise ValueError('Wrong identity or expired exact slot; never roll over')
 if not request['owner_approved_exact_full_file']:raise ValueError('Exact full-film owner authorization required')
 qa=request['qa'];assert qa['full_decode_passed'] and qa['audio_tail']['audio_tail_checked'] and qa['movie_sha256']==request['new_video_sha256']
 assert (60 if qa['profile']=='news' else 90)<qa['duration']<180
 path=Path('/tmp/replacement-approved.mp4');import requests
 with requests.get(request['new_media_url'],stream=True,timeout=120) as r:
  r.raise_for_status()
  with path.open('wb') as out:
   for chunk in r.iter_content(1024*1024):out.write(chunk)
 if hashlib.sha256(path.read_bytes()).hexdigest()!=request['new_video_sha256']:raise ValueError('Hosted approved movie bytes differ')
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(path),'-f','null','-'],check=True)
 key=request['episode_key'];entry=local()['episodes'][key]
 if entry['video_sha256'] not in (request['old_video_sha256'],request['new_video_sha256']):raise ValueError('Ledger movie changed since authorization')
 mapping=destinations(qa['profile']);assert set(mapping)==set(request['posts'])
 snapshots={}
 for service,receipt in request['posts'].items():
  assert entry['receipts'][service]['id']==receipt['id'] and mapping[service]['channel']==receipt['channel_id']
  rows=queued(mapping[service],request['due_at'],include_errors=True)
  if {p['id'] for p in rows}!={receipt['id']}:raise ValueError('Queue contains missing or additional post; no duplicate creation')
  p=lookup(receipt['id']);is_new=[a['source'] for a in p.get('assets',[])]==[request['new_media_url']];verify(p,receipt,request,new=is_new);payload(p,request);snapshots[service]=p
 def begin(data):
  audit=data.setdefault('approved_media_replacements',{}).setdefault(request['request_id'],{'request':request,'original_episode':copy.deepcopy(data['episodes'][key]),'posts':{},'created_posts':0})
  for service,p in snapshots.items():audit['posts'].setdefault(service,{'before':p,'phase':'preflight_verified'})
 mutate(begin)
 def progress(service,**values):
  def save(data):data['approved_media_replacements'][request['request_id']]['posts'][service].update(values)
  mutate(save)
 for service,receipt in request['posts'].items():
  p=lookup(receipt['id']);is_new=[a['source'] for a in p.get('assets',[])]==[request['new_media_url']]
  verify(p,receipt,request,new=is_new)
  if not is_new:
   prior=local()['approved_media_replacements'][request['request_id']]['posts'][service]
   if prior['phase'] in ('intent','uncertain','acknowledged'):raise ValueError('Previous edit unresolved; reconcile, never blindly resubmit')
   if datetime.now(timezone.utc)>=due:raise ValueError('Exact slot expired; do not send or roll over')
   progress(service,phase='intent')
   try:
    result=query('mutation ReplaceApprovedFilm($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{id dueAt}} ... on MutationError{message}}}',{'input':payload(p,request)})['editPost']
    if result.get('post',{}).get('id')!=receipt['id']:raise ValueError('Edit not acknowledged: '+str(result.get('message','unknown'))[:300])
    progress(service,phase='acknowledged',ack=result['post'])
   except Exception:
    progress(service,phase='uncertain');raise
  after=lookup(receipt['id']);verify(after,receipt,request);progress(service,phase='verified',after=after,verified_at=datetime.now(timezone.utc).isoformat())
 def finish(data):
  audit=data['approved_media_replacements'][request['request_id']];assert all(p['phase']=='verified' for p in audit['posts'].values())
  old=copy.deepcopy(audit['original_episode']);old.update(status='superseded_before_publication',superseded_by=request['request_id'],receipts_historical_only=True)
  for receipt in old.get('receipts',{}).values():receipt['historical_only']=True
  data['episodes'].setdefault(key+'-superseded-by-identity',old)
  e=data['episodes'][key]
  e.update(status='scheduled',title=request['story']['title'],canonical_subject=request['story']['canonical_subject'],story_document=request['story'],story_sha256=qa['original_story_sha256'],audio_sha256=qa['original_voice_sha256'],timing_sha256=request['timing_sha256'],duration=qa['duration'],video_sha256=request['new_video_sha256'],media_url=request['new_media_url'],source=request['story'].get('source',{}),source_selection={'canonical_subject':request['story']['canonical_subject'],'replacement_request':request['request_id']},source_document=request['story'].get('source',{}),editorial_review=request['story'].get('editorial_review'),approved_media_replacement=request['request_id'],retained_qa_provenance=qa,render_run=os.environ['GITHUB_RUN_ID'])
  for service,receipt in e['receipts'].items():receipt.update(media_url=request['new_media_url'],phase='verified',status='scheduled',verified_at=audit['posts'][service]['verified_at'],replacement_request=request['request_id'])
  audit.update(complete=True,completed_at=datetime.now(timezone.utc).isoformat(),same_post_ids=[x['id'] for x in request['posts'].values()])
 mutate(finish)
 output=local()['approved_media_replacements'][request['request_id']];Path('replacement-output').mkdir(exist_ok=True);Path('replacement-output/verified.json').write_text(json.dumps(output,ensure_ascii=False,indent=2))
 print(json.dumps({'complete':True,'due_at':request['due_at'],'same_post_ids':output['same_post_ids'],'created_posts':0}))
if __name__=='__main__':main()
