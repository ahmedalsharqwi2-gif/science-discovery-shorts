"""Move exact existing Buffer posts to an owner-requested time; never creates posts."""
import copy,hashlib,json,os,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

def instant(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Aware publication time required')
    return result.astimezone(timezone.utc)

def unchanged(post):
    return {'channelId':post['channelId'],'text':post.get('text'),'assets':post.get('assets',[]),'shareMode':post.get('shareMode'),'schedulingType':post.get('schedulingType')}

def retime(item,old_due,new_due,progress,lookup,edit,checkpoint):
    before=lookup(item['id'])
    if before.get('id')!=item['id'] or before.get('channelId')!=item['channel_id']:
        raise ValueError('Post/channel identity mismatch; no edit')
    if before.get('status')!='scheduled' or not before.get('assets'):
        raise ValueError('Only an existing scheduled video can move')
    current=instant(before['dueAt'])
    if current not in (instant(old_due),instant(new_due)):raise ValueError('Unexpected current time; reconcile instead of overwriting')
    baseline=progress.get('before',before)
    if unchanged(before)!=unchanged(baseline):raise ValueError('Existing video/text changed; no edit')
    if current!=instant(new_due):
        if progress.get('phase') in ('intent','uncertain','acknowledged'):
            raise ValueError('Unresolved previous edit; read-only reconciliation required')
        progress.update(phase='intent',before=copy.deepcopy(before),old_receipt=copy.deepcopy(item),requested_due_at=new_due)
        checkpoint()
        try:
            result=edit(item['id'],new_due)
            if result.get('id')!=item['id']:raise ValueError('Provider did not acknowledge the same post ID')
            progress.update(phase='acknowledged',ack=copy.deepcopy(result));checkpoint()
        except Exception:
            progress.update(phase='uncertain');checkpoint();raise
    after=lookup(item['id'])
    if after.get('id')!=item['id'] or after.get('status')!='scheduled' or instant(after['dueAt'])!=instant(new_due) or unchanged(after)!=unchanged(baseline):
        raise ValueError('Independent lookup did not prove the same unchanged video at the requested time')
    progress.update(phase='verified',after=copy.deepcopy(after),verified_at=datetime.now(timezone.utc).isoformat())
    checkpoint()
    return after

def query(text):
    import requests
    key=os.environ['BUFFER_API_KEY'].strip()
    if not key:raise ValueError('Missing this repository Buffer key')
    r=requests.post('https://api.buffer.com',headers={'Authorization':'Bearer '+key},json={'query':text},timeout=45)
    r.raise_for_status();data=r.json()
    if data.get('errors'):raise RuntimeError('Buffer query rejected; response body omitted')
    return data['data']

FIELDS='id channelId status dueAt text shareMode schedulingType assets { source }'
def lookup(identifier):
    return query('query { post(input: {id: '+json.dumps(identifier)+'}) { '+FIELDS+' } }')['post']
def edit(identifier,due):
    result=query('mutation { editPost(input: {id: '+json.dumps(identifier)+', dueAt: '+json.dumps(due)+'}) { ... on PostActionSuccess { post {id dueAt} } ... on MutationError {message} } }')['editPost']
    if not result.get('post'):raise RuntimeError('Buffer did not accept the same-post date edit')
    return result['post']

def check_queue(items,due):
    channels=[r['channel_id'] for r in items.values()];owned={r['id'] for r in items.values()}
    organizations=query('query { account {organizations {id}} }')['account']['organizations']
    start=(instant(due)-timedelta(seconds=1)).isoformat();end=(instant(due)+timedelta(seconds=1)).isoformat()
    for org in organizations:
        cursor=None
        for _ in range(20):
            after=', after: '+json.dumps(cursor) if cursor else ''
            result=query('query {posts(first:100'+after+', input:{organizationId:'+json.dumps(org['id'])+', filter:{channelIds:'+json.dumps(channels)+',dueAt:{start:'+json.dumps(start)+',end:'+json.dumps(end)+'},status:[scheduled,sending,sent]}}) {edges {node {id channelId dueAt}} pageInfo {hasNextPage endCursor}}}')['posts']
            for edge in result['edges'] or []:
                post=edge['node']
                if post['channelId'] in channels and instant(post['dueAt'])==instant(due) and post['id'] not in owned:
                    raise ValueError('Another post occupies an intended channel/time; no duplicate submission')
            if not result['pageInfo']['hasNextPage']:break
            cursor=result['pageInfo']['endCursor']
        else:raise ValueError('Queue inspection exceeded bounded pagination')

def main():
    request=json.loads(Path('.github/reschedule-existing-posts.json').read_text())
    if os.environ['GITHUB_REPOSITORY']!=request['repository']:raise ValueError('Repository ownership mismatch')
    due=request['new_due_at'];local=instant(due).astimezone(ZoneInfo('Africa/Cairo'))
    if (local.hour,local.minute,local.second)!=(17,0,0) or instant(due)<=datetime.now(timezone.utc):raise ValueError('Requested exact17:00 slot expired or invalid; never roll over')
    statepath=Path('state/professional_topics.json');data=json.loads(statepath.read_text())
    episode=next(r for r in data['episodes'] if r['slot']==request['slot'])
    if episode.get('publication_video_sha256')!=request['video_sha256']:raise ValueError('Existing film fingerprint differs')
    for service,item in request['posts'].items():
        receipt=episode['receipts'][service]
        if receipt['id']!=item['id'] or receipt['channel_id']!=item['channel_id']:raise ValueError('Exact existing receipts required')
    check_queue(request['posts'],due)
    # Validate every destination before making any edit.
    for service,item in request['posts'].items():
        before=lookup(item['id'])
        if before.get('channelId')!=item['channel_id'] or before.get('status')!='scheduled' or instant(before['dueAt']) not in (instant(request['old_due_at']),instant(due)):
            raise ValueError('Destination preflight failed; nothing edited')
    audit=data.setdefault('rescheduling_history',{}).setdefault(request['request_id'],{'old_due_at':request['old_due_at'],'requested_due_at':due,'posts':{},'original_episode_receipts':copy.deepcopy(episode['receipts'])})
    def checkpoint():
        statepath.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
        subprocess.run(['python','-m','professional_motion.persist_state'],check=True,stdout=subprocess.DEVNULL)
    for service,item in request['posts'].items():
        progress=audit['posts'].setdefault(service,{})
        actual=retime(item,request['old_due_at'],due,progress,lookup,edit,checkpoint)
        episode['receipts'][service].update(previous_due_at=request['old_due_at'],due_at=due,scheduled_at=actual['dueAt'],status=actual['status'],verified_at=progress['verified_at'],reschedule_request=request['request_id'])
        checkpoint()
    episode['due_at']=due
    stockpath=Path('state/publication_stock.json')
    if stockpath.exists():
        stock=json.loads(stockpath.read_text());oldkey='stock '+instant(request['old_due_at']).astimezone(ZoneInfo('Africa/Cairo')).date().isoformat()+' 17 Cairo'
        newkey='stock '+local.date().isoformat()+' 17 Cairo';slots=stock.setdefault('slots',{})
        if oldkey in slots:
            old=slots[oldkey]
            audit.setdefault('original_stock_record',copy.deepcopy(old))
            revised=copy.deepcopy(old);revised.update(receipts=copy.deepcopy(episode['receipts']),rescheduled_from=oldkey)
            for row in revised.get('submissions',{}).values():row['scheduled_at']=due
            historykey='rescheduled '+oldkey+' to '+newkey+' '+request['request_id']
            slots.setdefault(historykey,copy.deepcopy(old))
            slots[historykey].update(historical_only=True,rescheduled_to=newkey)
            slots[newkey]=revised
            slots[oldkey]={'confirmed':False,'receipts':{},'submissions':{},'required_services':old.get('required_services',[]),'prior_reschedule_history_key':historykey}
            audit['preserved_stock_history_key']=historykey
            stockpath.write_text(json.dumps(stock,ensure_ascii=False,indent=2)+'\n')
    audit.update(complete=True,completed_at=datetime.now(timezone.utc).isoformat(),created_posts=0,edited_existing_ids=[v['id'] for v in request['posts'].values()])
    checkpoint()
    Path('work').mkdir(exist_ok=True)
    Path('work/reschedule-result.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'complete':True,'new_due_at':due,'same_post_ids':audit['edited_existing_ids'],'created_posts':0},indent=2))
if __name__=='__main__':main()
