"""One explicitly requested new episode, with durable pre-writing intent and no rollover."""
import argparse,copy,hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from professional_motion import editorial

def request_for(profile):
    request=json.loads(Path('.github/produce-new-today.json').read_text())
    if request['profile']!=profile or os.environ.get('GITHUB_REPOSITORY')!='ahmedalsharqwi2-gif/'+request['repository']:
        raise ValueError('Request must match this repository and profile')
    due=datetime.fromisoformat(request['due_at'].replace('Z','+00:00'))
    local=due.astimezone(ZoneInfo('Africa/Cairo'))
    if due<=datetime.now(timezone.utc) or (local.hour,local.minute,local.second)!=(17,0,0):
        raise ValueError('Requested17:00 publication slot expired or invalid; never move it automatically')
    return request

def checkpoint():
    subprocess.run(['python','-m','professional_motion.persist_state'],check=True)

def decide(profile):
    request=request_for(profile);data=editorial.registry()
    existing=next((r for r in data['episodes'] if r['slot']==request['slot']),None)
    complete=bool(existing and existing.get('status') in ('scheduled','published') and len(existing.get('receipts',{}))==3)
    result={'run':not complete,'publish':not complete,'due':request['due_at'],'slot':request['slot'],'profile':profile}
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as output:
            for k,v in result.items():output.write(k+'='+(str(v).lower() if isinstance(v,bool) else str(v))+'\n')
    print(json.dumps(result))

def prepare(profile,slot):
    request=request_for(profile)
    if slot!=request['slot']:raise ValueError('Explicit requested slot required')
    data=editorial.registry();existing=next((r for r in data['episodes'] if r['slot']==slot),None)
    history=copy.deepcopy([r.get('story',{}) for r in data['episodes'] if r['slot']!=slot])
    attempts=data.setdefault('requested_production',{})
    prior=attempts.get(slot)
    retained=request.get('retained_draft')
    if prior and prior.get('phase')=='writing' and not (existing and existing.get('story')) and not retained and not (profile=='news' and request.get('news_source')):
        raise RuntimeError('Earlier writing attempt retained; resume its saved draft instead of generating again')
    if not existing:
        attempts.setdefault(slot,{'started_at':datetime.now(timezone.utc).isoformat()}).update(phase='writing',request_id=request['request_id'],due_at=request['due_at'])
        if retained:attempts[slot]['retained_draft_source_run']=retained['source_run']
        editorial.save(data);checkpoint()
    from .requested_editorial import editor,validate,require_novel_story
    original_candidates=editorial.candidates
    if profile=='news' and request.get('news_source'):
        source=copy.deepcopy(request['news_source'])
        from .news_policy import require_fresh
        require_fresh(source)
        source.update(key=hashlib.sha256(editorial.canonical(source['url']).encode()).hexdigest()[:16],family='compute',variant='chip')
        editorial.candidates=lambda actual:[copy.deepcopy(source)] if actual=='news' else original_candidates(actual)
    original_ask=editorial.ask
    if retained:
        draftpath=Path(retained['path']).resolve()
        if not draftpath.is_relative_to(Path('reviews/requested').resolve()) or hashlib.sha256(draftpath.read_bytes()).hexdigest()!=retained['sha256']:
            raise ValueError('Exact retained draft proof required')
        draft=json.loads(draftpath.read_text());used=False
        def use_retained(*args,**kwargs):
            nonlocal used
            if used:raise RuntimeError('No repeated writing-provider request allowed during saved-draft recovery')
            used=True;return copy.deepcopy(draft)
        editorial.ask=use_retained
    try:
        with editor(editorial,profile):story=editorial.prepare(profile,slot)
    finally:editorial.ask=original_ask;editorial.candidates=original_candidates
    validate(story,profile);require_novel_story(story,history)
    if profile!='news':
        story['editorial_review']={'performed':False,'required':False,'reason':'Owner permits general knowledge and original fiction without mandatory external sources or independent fact-check'}
    data=editorial.registry()
    row=next(r for r in data['episodes'] if r['slot']==slot)
    row['story']=story;row['requested_due_at']=request['due_at']
    data.setdefault('requested_production',{}).setdefault(slot,{}) .update(phase='story_ready',request_id=request['request_id'],due_at=request['due_at'],topic_key=story['topic_key'])
    editorial.save(data)
    path=editorial.ROOT/'delivery/story.json';path.parent.mkdir(exist_ok=True,parents=True);path.write_text(json.dumps(story,ensure_ascii=False,indent=2))
    checkpoint()
    print(json.dumps({'slot':slot,'topic_key':story['topic_key'],'words':sum(len(s['narration'].split()) for s in story['scenes']),'original_fiction':bool(story.get('fiction'))},ensure_ascii=False))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['decision','prepare']);parser.add_argument('profile');parser.add_argument('--slot');args=parser.parse_args()
    decide(args.profile) if args.action=='decision' else prepare(args.profile,args.slot)
if __name__=='__main__':main()
