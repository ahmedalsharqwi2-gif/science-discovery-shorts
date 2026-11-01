"""Source-driven shot planning with executable asset IDs and structural novelty.

Titles, colors, random seeds and prose are intentionally excluded from the
novelty signature. New narration alone cannot disguise the same eight shots.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path

FIELDS=('setting','focal_object','action','shot')

def load_catalog(repository, profile):
    root=Path(repository)
    for relative in ('professional_motion/director_catalog.json','stickman/director_catalog.json'):
        path=root/relative
        if path.is_file():
            catalog=json.loads(path.read_text())
            if catalog.get('version')!=1 or catalog.get('profile',profile)!=profile or not isinstance(catalog.get('worlds'),dict):
                raise ValueError('A matching executable director catalog is required')
            return catalog
    raise ValueError('No topic director catalog is installed; do not use a generic visual fallback')

def validate_plan(story,catalog):
    plan=story.get('visual_plan')
    if not isinstance(plan,dict) or plan.get('version')!=1:
        raise ValueError('Each new film requires an explicit topic-driven visual plan')
    worlds=catalog['worlds'];world=plan.get('world')
    if world not in worlds:raise ValueError('Visual world is not implemented')
    specification=worlds[world];rows=plan.get('scenes',[]);scenes=story.get('scenes',[])
    contract=specification.get('subject_contract',{})
    # Editorial model drafts do not yet have the repository-added source identity.
    # The assembled story is checked again before reservation and provider use.
    if 'topic_key' in story or 'source' in story:
        supported=contract.get('supported_topic_keys',[])
        if supported and story.get('topic_key') not in supported:
            raise ValueError('Visual geometry belongs to a different documented subject')
        fragment=contract.get('required_source_url_contains')
        if fragment and fragment not in story.get('source',{}).get('url',''):
            raise ValueError('Visual geometry requires its specific documented source')
    if len(rows)!=8 or len(scenes)!=8 or len({s.get('id') for s in scenes})!=8:
        raise ValueError('Eight uniquely authored and directed scenes required')
    if 'fiction' in specification and story.get('fiction') is not specification['fiction']:
        raise ValueError('Fictional settings must not be presented as documented events')
    allowed={'setting':specification.get('settings',[]),'focal_object':specification.get('focal_objects',specification.get('objects',[])),
             'action':specification.get('actions',[]),'shot':specification.get('shots',[])}
    compatible=specification.get('compatible_beats',[])
    if isinstance(compatible,dict):compatible=list(compatible.values())
    for scene,row in zip(scenes,rows):
        if row.get('id')!=scene.get('id'):raise ValueError('Directed shots must match authored scene identities')
        for field in FIELDS:
            if row.get(field) not in allowed[field]:raise ValueError('Unsupported executable '+field)
        if compatible and not any(all(row.get(field)==beat.get(field) for field in ('setting','focal_object','action')) and
                                  ('shot' not in beat or row.get('shot')==beat['shot']) for beat in compatible):
            raise ValueError('Action/object does not belong to the selected physical setting')
        if not isinstance(row.get('state_change'),str) or not row['state_change'].strip():
            raise ValueError('Each scene needs a concrete visible event and consequence')
        if 'source_excerpt_id' in row and 'evidence_excerpt_id' in scene and row['source_excerpt_id']!=scene['evidence_excerpt_id']:
            raise ValueError('Visual event and narration must use the same supporting source excerpt')
    minimum=int(specification.get('minimum_distinct_settings',3))
    if len({row['setting'] for row in rows})<minimum or len({row['action'] for row in rows})<4 or len({row['focal_object'] for row in rows})<4 or len({row['shot'] for row in rows})<3:
        raise ValueError('A film must vary physical settings, focal subjects, meaningful actions and shot scales')
    return plan

def signature(plan):
    payload={'world':plan['world'],'beats':[[row[field] for field in FIELDS] for row in plan['scenes']]}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def require_novel_plan(plan, previous):
    for old in previous:
        if not isinstance(old,dict) or old.get('world')!=plan['world'] or len(old.get('scenes',[]))!=8:continue
        meaningful=0
        for a,b in zip(plan['scenes'],old['scenes']):
            # Camera or new captions by themselves do not constitute a new scene.
            changes=sum(a.get(field)!=b.get(field) for field in FIELDS)
            physical=any(a.get(field)!=b.get(field) for field in ('setting','focal_object','action'))
            meaningful+=bool(physical and changes>=2)
        if signature(plan)==signature(old) or meaningful<4:
            raise ValueError('Visual sequence repeats an earlier film; changing text, palette or camera alone is insufficient')
    return signature(plan)

def align_plan_ids(story):
    """Reconcile metadata IDs only when scene/source correspondence is unambiguous."""
    result=deepcopy(story)
    scenes=result.get('scenes',[]);plan=result.get('visual_plan',{});rows=plan.get('scenes',[])
    if len(scenes)!=8 or len(rows)!=8:return result
    ids=[s.get('id') for s in scenes];row_ids=[r.get('id') for r in rows]
    if len(set(ids))!=8 or len(set(row_ids))!=8:return result
    if set(ids)==set(row_ids):
        by_id={r['id']:r for r in rows};plan['scenes']=[by_id[i] for i in ids]
    elif all(isinstance(s.get('evidence_excerpt_id'),int) and not isinstance(s.get('evidence_excerpt_id'),bool)
             and r.get('source_excerpt_id')==s['evidence_excerpt_id'] for s,r in zip(scenes,rows)):
        for scene,row in zip(scenes,rows):row['id']=scene['id']
    return result

def response_schema(base,catalog):
    schema=deepcopy(base);worlds=catalog['worlds']
    choices={field:sorted({value for spec in worlds.values() for value in spec.get(key,[])}) for field,key in
             [('setting','settings'),('focal_object','focal_objects'),('action','actions'),('shot','shots')]}
    fields={key:{'type':'STRING','description':'Executable asset ID; validated against the supplied catalog after generation.'} for key in choices}
    fields.update(id={'type':'STRING'},state_change={'type':'STRING'},source_excerpt_id={'type':'INTEGER'})
    schema['properties']['visual_plan']={'type':'OBJECT','properties':{'version':{'type':'INTEGER'},'topic_key':{'type':'STRING'},'world':{'type':'STRING','description':'Implemented catalog world ID, or unsupported when no world fits the source.'},
        'scenes':{'type':'ARRAY','maxItems':8,'items':{'type':'OBJECT','properties':fields,'required':list(fields)}}},'required':['version','world','scenes']}
    schema['required']=[*schema['required'],'visual_plan']
    return schema

def prompt_instructions(catalog):
    return ('\nDIRECT THIS SPECIFIC FILM, not a reusable slide/template sequence. Replace any earlier fixed scene-order instruction. '
        'Copy each narration scene id EXACTLY to its matching visual row id; bind both rows to the same source excerpt. Choose an implemented visual world appropriate to the exact source and write visual_plan version1, with topic_key equal to the candidate key. '
        'Every scene selects real setting, focal_object, action and shot IDs from the supplied executable catalog, and states the visible state_change caused by that action. '
        'The source excerpt ID must match that scene narration evidence_excerpt_id. Select and order physical locations, props, actions and shots to tell THIS story: question/goal, obstacle or mechanism, revealing actions and concrete payoff. '
        'Do not follow the catalog listing order mechanically; it is an asset vocabulary, not the plot. '
        'Use establishing, interaction and close detail views; the environment fills the frame. Do not leave a tiny object on the same black background for eight scenes. '
        'A repeated world must still have a different physically meaningful shot sequence; new text/colors/randomness are not visual novelty. '
        'Do not invent historical actions or measurements: label explanatory reconstructions as schematic; fictional worlds require explicit fiction. '
        'If the supplied source cannot be told using real supported assets, suitable=false and world=unsupported. CATALOG:\n'+json.dumps(catalog,ensure_ascii=False))

@contextmanager
def directing_editor(editorial,catalog,previous):
    original_schema,original_ask=editorial.SCHEMA,editorial.ask
    editorial.SCHEMA=response_schema(original_schema,catalog)
    def ask(prompt,schema,**kwargs):
        directed='visual_plan' in schema.get('properties',{})
        if directed:
            if 'Scene order: ' in prompt and '. Treat source text' in prompt:
                before,tail=prompt.split('Scene order: ',1);_,after=tail.split('. Treat source text',1)
                prompt=before+'Source-driven visual order follows visual_plan. Treat source text'+after
            prompt+=prompt_instructions(catalog)
            prompt+='\nRECENT EXECUTED/RESERVED VISUAL SEQUENCES (avoid repeating these physical compositions): '+json.dumps([{'world':p.get('world'),'beats':[{field:r.get(field) for field in FIELDS} for r in p.get('scenes',[])]} for p in previous[-10:]],ensure_ascii=False)
        if kwargs.get('review') and {'supported','novel'} <= set(schema.get('properties',{})):
            prompt+='\nAlso independently review visual_plan: each physical setting, focal object, action and state change must explain that specific narration and source, not be decorative or randomly reordered. Reject an unsupported source-to-asset mapping or an incoherent causal sequence. Do not approve eight repetitions of one composition.'
        result=original_ask(prompt,schema,**kwargs)
        for attempt in range(2):
            if directed:
                if getattr(editorial,'ROOT',None) is not None:
                    folder=Path(editorial.ROOT)/'delivery';folder.mkdir(parents=True,exist_ok=True)
                    raw=json.dumps(result,ensure_ascii=False,indent=2)
                    (folder/('director-draft-'+hashlib.sha256(raw.encode()).hexdigest()[:16]+'.json')).write_text(raw)
                result=align_plan_ids(result)
            if not directed or result.get('suitable') is not True:break
            temporary={**result,'fiction':result.get('fiction',False)}
            world=result.get('visual_plan',{}).get('world')
            if world in catalog['worlds'] and 'fiction' in catalog['worlds'][world]:temporary['fiction']=catalog['worlds'][world]['fiction']
            try:
                plan=validate_plan(temporary,catalog);require_novel_plan(plan,previous)
                break
            except ValueError as error:
                if attempt:raise
                repair=(prompt+'\nVISUAL PLAN REPAIR: '+str(error)+'. Keep the exact source-backed narration and subject. Fix only executable shot choices and meaningful event staging, maintaining a coherent causal order; never randomize shots to pass a test. DRAFT: '+json.dumps(result,ensure_ascii=False))
                result=original_ask(repair,schema,**kwargs)
        return result
    editorial.ask=ask
    try:yield
    finally:editorial.SCHEMA,editorial.ask=original_schema,original_ask
