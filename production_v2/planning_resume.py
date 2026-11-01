"""Recover one failed pre-reservation draft; never regenerate its text."""
from contextlib import contextmanager
from copy import deepcopy
import io,json,os,zipfile
from pathlib import PurePosixPath
from .diagnose import Reader
from .export_review import context

def read_draft(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        stories=[n for n in archive.namelist() if n.endswith('/professional_motion/delivery/story.json')]
        names=stories if len(stories)==1 else [n for n in archive.namelist() if PurePosixPath(n).name=='last-draft.json']
        failures=[n for n in archive.namelist() if PurePosixPath(n).name=='generation-failure.json']
        if len(names)!=1 or len(failures)!=1:raise ValueError('Require one retained draft and failure evidence')
        for name in names+failures:
            path=PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or archive.getinfo(name).file_size>512*1024:
                raise ValueError('Invalid retained draft archive')
        failure=json.loads(archive.read(failures[0]))
        if failure.get('reservation_retained') is not False or failure.get('failed_phase')!='story_or_reservation':
            raise ValueError('Reserved stories require exact ledger/voice resume; no new reservation')
        draft=json.loads(archive.read(names[0]))
        if len(draft.get('scenes',[]))!=8 or draft.get('suitable') is not True:
            raise ValueError('No complete suitable retained draft')
        return draft

@contextmanager
def planning_resume(profile,target_run):
    repository,run,attempt,source=context(profile)
    reader=Reader(repository,os.environ['GITHUB_TOKEN'])
    target=reader.json('/actions/runs/'+str(int(target_run)))
    if target.get('head_branch')!='codex/rebuild-production-v2' or target.get('conclusion')!='failure':
        raise ValueError('Resume requires an actual failed candidate-branch run')
    artifacts=reader.json('/actions/runs/'+str(int(target_run))+'/artifacts').get('artifacts',[])
    expected=profile+'-v2-fresh-candidate-'+str(target_run)
    matches=[a for a in artifacts if a.get('name') in (expected,profile+'-v2-final-'+str(target_run)) and not a.get('expired')]
    if len(matches)!=1:raise ValueError('Require exact retained candidate artifact')
    draft=read_draft(reader.archive('/actions/artifacts/'+str(matches[0]['id'])+'/zip'))
    from professional_motion import editorial
    original=editorial.ask;original_candidates=editorial.candidates;used=False
    if profile=='news' and draft.get('source',{}).get('url'):
        source_row={**draft['source'],'key':draft['topic_key'],'family':draft['visual_family'],'variant':draft['variant'],'news_selection':draft.get('news_selection',{})}
        editorial.candidates=lambda actual:[source_row] if actual==profile else original_candidates(actual)
    def retained(prompt,schema,**kwargs):
        nonlocal used
        if kwargs.get('review') or 'narrations' in schema.get('properties',{}):return original(prompt,schema,**kwargs)
        if used:
            if profile=='news' and ('EDITORIAL REVISION:' in prompt or 'Rewrite this SAME draft' in prompt):
                print(json.dumps({'targeted_retained_narration_revision':True,'new_topic_generation':False}))
                return original(prompt,schema,**kwargs)
            raise ValueError('Retained draft requires a targeted edit; automatic full-story regeneration is disabled')
        used=True
        print(json.dumps({'retained_draft_from_run':str(target_run),'story_generation_requests':0,'profile':profile}))
        return deepcopy(draft)
    editorial.ask=retained
    try:yield
    finally:editorial.ask=original;editorial.candidates=original_candidates
