"""Apply the owner's exact existing-post time change; never create or regenerate posts."""
import json
import re
from functools import partial
from datetime import datetime, timezone
from pathlib import Path
from .publish import destinations, query, queued, instant
from .state import identity, local, mutate
from .schedule import due_for, CAIRO, trial
from .health import write_json
FIELDS='id channelId status dueAt text assets {source} metadata {__typename ... on YoutubePostMetadata {title category {categoryId} privacy madeForKids notifySubscribers} ... on FacebookPostMetadata {type} ... on InstagramPostMetadata {type shouldShareToFeed}}'

def read_post(identifier):
    """Fetch one exact retained provider ID independently."""
    return query('query {post(input:{id:'+json.dumps(identifier)+'}) {'+FIELDS+'}}')['post']

def validate(post, identifier, channel, old_due, new_due, media):
    """Only the approved own scheduled post with its original media may move."""
    if post.get('id')!=identifier or post.get('channelId')!=channel or post.get('status')!='scheduled':
        raise ValueError('Exact owned scheduled post required; sent or missing posts cannot move')
    if instant(post['dueAt']) not in (instant(old_due),instant(new_due)):
        raise ValueError('Provider schedule changed independently; stop for reconciliation')
    if [a.get('source') for a in post.get('assets',[])] != [media]:
        raise ValueError('Retained media no longer matches the exact scheduled post')

def edit_input(service,identifier,request,before):
    """Preserve required network metadata exactly when the editor revalidates it."""
    payload={'id':identifier,'mode':'customScheduled','dueAt':request['target_due_at']}
    metadata=before.get('metadata') or {}
    keys={'youtube':('title','privacy','madeForKids','notifySubscribers'),'facebook':('type',),'instagram':('type','shouldShareToFeed')}.get(service,())
    retained={key:metadata[key] for key in keys if key in metadata and metadata[key] is not None}
    if service=='youtube' and metadata.get('category'):
        retained['categoryId']=metadata['category']['categoryId']
    if retained:payload['metadata']={service:retained}
    return payload

def reconcile_rejection(identifier,request,before,record,persist):
    """Allow one explicitly diagnosed rejection after a fresh unchanged-state read."""
    if record.get('phase') not in ('intent','uncertain'):return
    original=record.get('before',{})
    fields=('id','channelId','status','dueAt','text','assets')
    same=all(before.get(key)==original.get(key) for key in fields)
    if identifier not in request.get('reconciled_rejection_ids',[]) or record.get('reconciliation_used') or not same:
        raise ValueError('Uncertain prior time edit is not repeated automatically')
    record.update(phase='rejected_reconciled',reconciliation_used=True)
    persist()

def move_one(service, destination, identifier, request, entry, record, persist):
    """Retain intent, edit only dueAt/mode, then read back the same post ID."""
    before=read_post(identifier)
    validate(before,identifier,destination['channel'],request['source_due_at'],request['target_due_at'],entry['media_url'])
    if instant(before['dueAt'])!=instant(request['target_due_at']):
        reconcile_rejection(identifier,request,before,record,persist)
        record.update(phase='intent',post_id=identifier,before=before)
        persist()
        try:
            result=query('mutation ChangeApprovedSchedule($input:EditPostInput!){editPost(input:$input){__typename ... on PostActionSuccess{post{id dueAt}} ... on MutationError{message}}}',{'input':edit_input(service,identifier,request,before)})['editPost']
            if result.get('post',{}).get('id')!=identifier:
                message=re.sub(r'https?://\S+','[provider URL omitted]',str(result.get('message') or result.get('__typename') or 'unknown provider response'))[:400]
                actual=read_post(identifier)
                if instant(actual['dueAt'])==instant(request['source_due_at']):
                    record.update(phase='rejected',provider_message=message);persist()
                raise ValueError('Time edit rejected: '+message)
            record['phase']='acknowledged';persist()
        except Exception:
            if record.get('phase')!='rejected':record['phase']='uncertain'
            persist();raise
    actual=read_post(identifier)
    validate(actual,identifier,destination['channel'],request['target_due_at'],request['target_due_at'],entry['media_url'])
    original=record.get('before',before)
    if actual.get('text')!=original.get('text') or actual.get('assets')!=original.get('assets'):
        raise ValueError('Schedule edit changed text or media; inspect exact post before further actions')
    record.update(service=service,phase='verified',post_id=identifier,due_at=actual['dueAt'],verified_at=datetime.now(timezone.utc).isoformat())
    persist()
    return actual

def validate_request(req,repo,profile,entry):
    """Constrain time changes to the approved exact episode and future trial date."""
    if req.get('repository')!=repo or req.get('approved_by_owner') is not True:
        raise ValueError('Exact owner-approved repository request required')
    target=instant(req['target_due_at']);day=target.astimezone(CAIRO).date()
    if target<=datetime.now(timezone.utc) or not trial(day) or target!=due_for(day):
        raise ValueError('Only the approved future trial slot can be applied')
    if entry.get('video_sha256')!=req['video_sha256'] or entry.get('profile')!=profile:
        raise ValueError('Retained episode identity differs from the approved time-change target')
    if instant(entry['due_at']) not in (instant(req['source_due_at']),target):
        raise ValueError('Ledger has another independent schedule change')

def preflight(req,entry,profile):
    """Inspect all three owned destinations and target slots before any edit."""
    mapping=destinations(profile)
    if set(req['post_ids'])!=set(mapping) or len(mapping)!=3:
        raise ValueError('All three exact existing destinations required')
    observations={}
    for service,destination in mapping.items():
        identifier=req['post_ids'][service]
        if entry.get('receipts',{}).get(service,{}).get('id')!=identifier:
            raise ValueError('Approved post ID is not retained on this episode')
        observations[service]=read_post(identifier)
        validate(observations[service],identifier,destination['channel'],req['source_due_at'],req['target_due_at'],entry['media_url'])
        occupied=queued(destination,req['target_due_at'])
        if any(p.get('id')!=identifier for p in occupied):
            raise ValueError('Target slot has another post; no duplicate or overwrite')
    return mapping,observations

def save_change_record(slot,request_id,service,record):
    """Persist one provider edit intent without loop-bound mutable defaults."""
    def update(data):
        episode=data['episodes'][slot]
        episode.setdefault('time_change_receipts',{}).setdefault(request_id,{})[service]=dict(record)
    mutate(update)

def main():
    """Reconcile the approved three receipts with durable per-post edit intents."""
    req=json.loads(Path('.github/remotion-time-change.json').read_text())
    repo,profile=identity()
    entry=local()['episodes'][req['slot']]
    validate_request(req,repo,profile,entry)
    mapping,observations=preflight(req,entry,profile)
    if req.get('inspect_only'):
        write_json('reviews/schedule_changes/'+req['request_id']+'-inspection.json',{'request':req,'observed':observations,'publication_mutations':0})
        print('Read-only inspection complete; no Buffer mutation attempted')
        return
    proof_path='reviews/schedule_changes/'+req['request_id']+'.json'
    saved=Path(proof_path)
    if not saved.exists():
        write_json(proof_path,{'request':req,'before':observations,'complete':False,'generation_calls':0,'new_posts':0})
    results={}
    for service,destination in mapping.items():
        record=dict(entry.get('time_change_receipts',{}).get(req['request_id'],{}).get(service,{}))
        persist=partial(save_change_record,req['slot'],req['request_id'],service,record)
        results[service]=move_one(service,destination,req['post_ids'][service],req,entry,record,persist)
    def commit(data):
        episode=data['episodes'][req['slot']]
        episode.setdefault('schedule_history',[])
        if not any(h.get('request_id')==req['request_id'] for h in episode['schedule_history']):
            episode['schedule_history'].append({'request_id':req['request_id'],'from':req['source_due_at'],'to':req['target_due_at']})
        episode['due_at']=req['target_due_at']
        for service,post in results.items():
            episode['receipts'][service].update(due_at=req['target_due_at'],scheduled_at=post['dueAt'])
    mutate(commit)
    write_json(proof_path,{'request':req,'before':json.loads(saved.read_text()).get('before',observations),'after':results,'complete':True,'generation_calls':0,'new_posts':0,'verified_at':datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'complete':True,'date':instant(req['target_due_at']).astimezone(CAIRO).date().isoformat(),'due_at':req['target_due_at'],'post_ids':req['post_ids'],'generation_calls':0,'new_posts':0}))
if __name__=='__main__':main()
