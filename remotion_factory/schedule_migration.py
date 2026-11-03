"""Apply the owner's exact existing-post time change; never create or regenerate posts."""
import json
from datetime import datetime, timezone
from pathlib import Path
from .publish import destinations, query, queued, instant
from .state import identity, local, mutate
from .schedule import due_for, CAIRO, trial
from .health import write_json
FIELDS='id channelId status dueAt text assets {source}'

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

def move_one(service, destination, identifier, request, entry, record, persist):
    """Retain intent, edit only dueAt/mode, then read back the same post ID."""
    before=read_post(identifier)
    validate(before,identifier,destination['channel'],request['source_due_at'],request['target_due_at'],entry['media_url'])
    if instant(before['dueAt'])!=instant(request['target_due_at']):
        if record.get('phase') in ('intent','uncertain'):
            raise ValueError('Uncertain prior time edit is not repeated automatically')
        record.update(phase='intent',post_id=identifier,before=before)
        persist()
        try:
            result=query('mutation ChangeApprovedSchedule($input:EditPostInput!){editPost(input:$input){... on PostActionSuccess{post{id dueAt}} ... on MutationError{message}}}',{'input':{'id':identifier,'mode':'customScheduled','dueAt':request['target_due_at']}})['editPost']
            if result.get('post',{}).get('id')!=identifier:
                raise ValueError('Time edit was not acknowledged for the retained ID')
            record['phase']='acknowledged';persist()
        except Exception:
            record['phase']='uncertain';persist();raise
    actual=read_post(identifier)
    validate(actual,identifier,destination['channel'],request['target_due_at'],request['target_due_at'],entry['media_url'])
    original=record.get('before',before)
    if actual.get('text')!=original.get('text') or actual.get('assets')!=original.get('assets'):
        raise ValueError('Schedule edit changed text or media; inspect exact post before further actions')
    record.update(phase='verified',post_id=identifier,due_at=actual['dueAt'],verified_at=datetime.now(timezone.utc).isoformat())
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

def main():
    """Reconcile the approved three receipts with durable per-post edit intents."""
    req=json.loads(Path('.github/remotion-time-change.json').read_text())
    repo,profile=identity()
    entry=local()['episodes'][req['slot']]
    validate_request(req,repo,profile,entry)
    mapping,observations=preflight(req,entry,profile)
    proof_path='reviews/schedule_changes/'+req['request_id']+'.json'
    saved=Path(proof_path)
    if not saved.exists():
        write_json(proof_path,{'request':req,'before':observations,'complete':False,'generation_calls':0,'new_posts':0})
    results={}
    for service,destination in mapping.items():
        record=dict(entry.get('time_change_receipts',{}).get(req['request_id'],{}).get(service,{}))
        def persist(service=service,record=record):
            def update(data):
                episode=data['episodes'][req['slot']]
                episode.setdefault('time_change_receipts',{}).setdefault(req['request_id'],{})[service]=dict(record)
            mutate(update)
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
