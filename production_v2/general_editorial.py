"""Broad knowledge and original fiction authoring without mandatory external sources."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib,json,re
from pathlib import Path

CATEGORIES={'science':['biology','chemistry','medicine_and_body','geology','physics','environment','astronomy'],
'history':['daily_life','inventions','civilizations','trade','cities','historical_events'],
'horror':['supernatural','psychological','mystery','isolated_places']}
ASSETS=('cell','leaf','heart','dna','molecule','crystal','rock_layers','volcano','tree','pendulum','gear','magnet','circuit','river','fossil','scroll','book','temple','house','ship','cart','person','stickman','door','clock','lantern','table','sphere','box','cylinder','cone','torus')
MOTIONS=('none','spin','pulse','drift','orbit','grow','assemble','split','swing','flow')
ENVIRONMENTS=('laboratory','body_section','landscape','geology_section','workshop','ancient_city','harbor','dark_interior','forest','ocean')

def enabled(profile,root='.'):
    path=Path(root)/'config/editorial_policy.json'
    if profile not in CATEGORIES or not path.is_file():return False
    policy=json.loads(path.read_text())
    return policy.get('profile')==profile and policy.get('external_sources_required') is False

def validate(story,profile):
    if story.get('profile')!=profile or not story.get('topic_key') or len(story.get('scenes',[]))!=8:
        raise ValueError('A new identified eight-scene story is required')
    if story.get('knowledge_category') not in CATEGORIES[profile]:raise ValueError('Unknown editorial category')
    signatures=[]
    def vector(value,minimum,maximum):
        return isinstance(value,list) and len(value)==3 and all(isinstance(v,(float,int)) and not isinstance(v,bool) and minimum<=v<=maximum for v in value)
    for scene in story['scenes']:
        if not scene.get('narration') or not scene.get('label') or not scene.get('visual_change'):
            raise ValueError('Narration, heading and visible causal change required')
        if scene.get('environment') not in ENVIRONMENTS:raise ValueError('Unsupported environment')
        objects=scene.get('objects',[])
        if not 3<=len(objects)<=16:raise ValueError('Three to sixteen authored objects required per scene')
        for obj in objects:
            if obj.get('kind') not in ASSETS or obj.get('motion') not in MOTIONS:raise ValueError('Unimplemented subject or motion')
            if not vector(obj.get('position'),-6,6) or not vector(obj.get('scale'),.08,5) or not vector(obj.get('rotation'),-6.3,6.3):
                raise ValueError('Object transform exceeds scene bounds')
            if not re.fullmatch(r'#[0-9a-fA-F]{6}',obj.get('color','')):raise ValueError('Explicit object color required')
        for key in ('camera_start','camera_end'):
            if not vector(scene.get(key),-25,25) or scene[key][2]<5:raise ValueError('A safe authored camera path required')
        signatures.append(hashlib.sha256(json.dumps({'environment':scene['environment'],'objects':[{k:o[k] for k in ('kind','position','scale','motion')} for o in objects]},sort_keys=True).encode()).hexdigest())
    if len(set(signatures))<5:raise ValueError('Text or color changes cannot disguise repeated scene geometry')
    story['visual_plan']={'version':1,'world':'procedural_story','scenes':[{'id':s['id'],'setting':s['environment'],'focal_object':s['objects'][0]['kind'],'action':s['objects'][0]['motion'],'shot':'authored_camera','state_change':s['visual_change']} for s in story['scenes']]}
    story['visual_sequence_sha256']=hashlib.sha256(json.dumps(signatures).encode()).hexdigest()
    return story

def prepare(editorial,profile,slot):
    data=editorial.registry()
    existing=next((r for r in data['episodes'] if r.get('slot')==slot),None)
    if existing and existing.get('story'):
        story=validate(existing['story'],profile)
        (editorial.ROOT/'delivery/story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2));return story
    previous=editorial.prior()
    counts={category:sum(r.get('knowledge_category',r.get('story',{}).get('knowledge_category'))==category for r in previous if isinstance(r,dict)) for category in CATEGORIES[profile]}
    category=min(counts,key=counts.get)
    base=deepcopy(editorial.SCHEMA)
    base['properties'].pop('visual_plan',None);base['required']=[k for k in base['required'] if k!='visual_plan']
    scene=base['properties']['scenes']['items']
    scene['properties'].pop('evidence_excerpt_id',None);scene['required']=[k for k in scene['required'] if k!='evidence_excerpt_id']
    vector={'type':'ARRAY','items':{'type':'NUMBER'},'minItems':3,'maxItems':3}
    obj={'type':'OBJECT','properties':{'kind':{'type':'STRING'},'position':deepcopy(vector),'scale':deepcopy(vector),'rotation':deepcopy(vector),'color':{'type':'STRING'},'motion':{'type':'STRING'}},'required':['kind','position','scale','rotation','color','motion']}
    scene['properties'].update(environment={'type':'STRING'},objects={'type':'ARRAY','items':obj},camera_start=deepcopy(vector),camera_end=deepcopy(vector),visual_change={'type':'STRING'})
    scene['required']+=['environment','objects','camera_start','camera_end','visual_change']
    old=[{'title':r.get('title',''),'subject':r.get('canonical_subject',r.get('topic_key','')),'plot':r.get('plot_signature','')} for r in previous if isinstance(r,dict)][-600:]
    prompt=('Author one NEW full Egyptian Arabic film for '+profile+', category '+category+'. '
     'The owner does not require external sources or an independent scientific fact-check step. Do not browse, cite or fabricate references. '
     'Science covers ALL sciences: biology, chemistry, the human body, geology, physics, environment and astronomy; do not turn non-astronomy topics into space or NASA stories. '
     'History should tell a compelling broadly known historical event, invention, daily-life process or civilization, without inventing precise quotations, witnesses or references. '
     'Horror is an ORIGINAL fictional story, with a character goal, mounting obstacle, concrete actions and a callback/twist ending. Do not present fiction as a true incident. '
     'Avoid every previous underlying topic or plot, not merely their titles. canonical_subject is a stable specific English slug without a date or random suffix. '
     'Write eight connected scenes totaling 300 to 340 spoken Egyptian Arabic words, naturally varied, with a direct hook and concrete payoff. No greetings, generic padding or subscribe appeals. '
     'Titles and headings are short Arabic. Three to five topical hashtags. Numbers in narration are pronounceable Arabic words. suitable=true. '
     'Compose DISTINCT 3D staged scenes, not eight copies of one object on black. The first object is the main subject and should occupy a substantial part of the frame. '
     'Each scene has 3 to 10 objects, with positions [-6,6], positive scales [0.08,5], rotations in radians [-6.3,6.3], hex colors, and an implemented motion. '
     'Camera start/end are [x,y,z], z between 7 and 19, looking toward the center [0,0,0]. Keep main subjects near the center and leave top/bottom caption areas clear. '
     'Use objects and motions to show what the narration says: causal action, changed state and consequence, not decorative random motion. '
     'Composite assets: cell includes membrane/nucleus; leaf includes stem/veins; heart is a schematic beating organ; dna is a double helix; molecule is bonded atoms; rock_layers is a cutaway; '
     'temple has columns/pediment; ship has hull/mast/sail; person/stickman has articulated limbs; door has a hinged panel; gear has teeth; circuit has a conducting route. '
     'Use schematic explanations without implying a measured simulation or exact historical reconstruction. '
     'Objects: '+json.dumps(ASSETS)+'. Motions: '+json.dumps(MOTIONS)+'. Environments: '+json.dumps(ENVIRONMENTS)+'. '
     'visual_mode=hero, labels are at most two short Arabic phrases copied from narration; facts and milestones may be empty. '
     'visual_change describes a specific visible event and outcome. PREVIOUS TOPICS/PLOTS, do not repeat: '+json.dumps(old,ensure_ascii=False))
    delivery=editorial.ROOT/'delivery';delivery.mkdir(parents=True,exist_ok=True)
    draft=editorial.ask(prompt,base,creative=profile=='horror')
    (delivery/'last-draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2))
    if draft.get('suitable') is not True:raise ValueError('Author did not provide a usable original story')
    subject=str(draft.get('canonical_subject','')).casefold().strip()
    if not subject or any(subject==str(r.get('subject','')).casefold().strip() for r in old):raise ValueError('Underlying subject already reserved')
    for i,s in enumerate(draft['scenes']):s['id']='scene_'+str(i+1)
    draft.update(profile=profile,series=editorial.BRANDS[profile],topic_key='knowledge-'+subject,knowledge_category=category,
                 visual_family='wave' if profile=='science' else 'architecture' if profile=='history' else 'haunted_interior',
                 variant='procedural',fiction=profile=='horror',documented=False,
                 source={'kind':'original_fiction' if profile=='horror' else 'general_knowledge','publisher':editorial.BRANDS[profile],'url':'','title':''},
                 editorial_policy={'external_sources_required':False,'independent_scientific_review_required':False})
    validate(draft,profile)
    if any(r.get('story',{}).get('visual_sequence_sha256')==draft['visual_sequence_sha256'] for r in previous if isinstance(r,dict)):
        raise ValueError('Visual sequence was already produced')
    data['episodes'].append({'slot':slot,'topic_key':draft['topic_key'],'canonical_subject':subject,'title':draft['title'],
       'knowledge_category':category,'status':'reserved','story':draft})
    editorial.save(data);(delivery/'story.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2))
    return draft

@contextmanager
def editor(editorial,profile):
    original=editorial.prepare
    editorial.prepare=lambda actual,slot:prepare(editorial,actual,slot)
    try:yield
    finally:editorial.prepare=original
