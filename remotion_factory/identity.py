"""Channel-specific visual direction; no narration, dates, voices or posts rewritten."""
import copy,hashlib,json,re
from pathlib import Path
VERSION='channel-identities-v1'
OBJECTS=('cell','bacterium','leaf','heart','dna','molecule','surfactant','micelle','crystal','rock_layers','volcano','tree','pendulum','gear','magnet','circuit','river','fossil','scroll','book','temple','egypt_temple','pyramid','house','ship','cart','person','sphere','server','monitor','robot','microphone','phone','chip','document','shield','network','waveform')
MOTIONS=('none','spin','pulse','drift','orbit','grow','assemble','split','swing','flow','shake','float')
SHOTS={'science':('experiment','macro','process','comparison','photo'),'history':('archive','place','artifact','reconstruction','chronology'),'horror':('archive','location','evidence','absence','reconstruction'),'news':('headline','product','workflow','comparison','takeaway'),'stickman':('impact','experiment','escalation','fail','discovery','adapt','solution','twist')}
IDENTITIES=('science','history','horror','news','stickman')

def identity(profile):
 from visual_contract import load_template
 t=load_template()
 if profile!=t['channel']:raise ValueError('Cross-channel identity is forbidden')
 return {'version':VERSION,'profile':profile,'name':t['display_name'],'background':t['palette']['bg'],'ink':t['palette']['ink'],'accent':t['palette']['accent'],'visual':json.loads((Path(__file__).resolve().parents[1]/'config/channel_identity.json').read_text())['visual'],'sound':json.loads((Path(__file__).resolve().parents[1]/'config/channel_identity.json').read_text())['sound']}
def schema_for(base,profile):
 value=copy.deepcopy(base);item=value['properties']['scenes']['items']
 item['properties'].update(shot_type={'type':'STRING','enum':list(SHOTS[profile])},hero_object={'type':'STRING','enum':list(OBJECTS)},object_motion={'type':'STRING','enum':list(MOTIONS)},image_query={'type':'STRING','description':'Exact English entity/place/object from this scene, 2–7 words; empty for a purely drawn scene. Never a URL.'},visual_rationale={'type':'STRING','description':'One concrete sentence explaining what changes on screen and why it matches the spoken words.'})
 item['properties'].update(secondary_object={'type':'STRING','enum':['none',*OBJECTS]},interaction={'type':'STRING','enum':['none','approach','separate','encircle','transfer','contrast']})
 item['required']=list(dict.fromkeys(item['required']+['secondary_object','interaction','shot_type','hero_object','object_motion','image_query','visual_rationale']))
 value['properties']['director_version']={'type':'STRING','enum':[VERSION]};value['required']=list(dict.fromkeys(value['required']+['director_version']))
 if profile=='stickman':
  for name in ['shot_type','hero_object','object_motion','secondary_object','interaction','image_query']:
   item['properties'].pop(name,None);item['required']=[key for key in item['required'] if key!=name]
  item['properties'].update(cause={'type':'STRING'},attempt={'type':'STRING'},consequence={'type':'STRING'})
  item['required']+=['cause','attempt','consequence']
 return value
def direction(profile):
 common=f'VISUAL IDENTITY {VERSION}: {json.dumps(identity(profile),ensure_ascii=False)}. Select shot_type from {SHOTS[profile]}; eight changes in the situation, NOT eight copies of one diagram. hero_object must be a literal object actually discussed, from {OBJECTS}; object_motion from {MOTIONS}. image_query identifies the actual subject in English, not a made-up event or random decorative image. visual_rationale describes a concrete visible action and its relation to narration. Use secondary_object and interaction to show a causal process: approach/separate/encircle/transfer/contrast, or none when not relevant. Both objects must be supported by the spoken mechanism; never decorate a true event with invented equipment. No generated JavaScript, URLs or fabricated screenshots. Do not describe illustrations as original footage.'
 if profile=='history':common+=' Tell a genuine event with decisions, obstacles and consequences. A monument description is not a complete story; identify what happened, who acted, what was at stake and the outcome. Real photographs, places and documents take precedence over text lists. Use egypt_temple for Abu Simbel and Egyptian statue temples, pyramid for pyramids; never replace them with a Greek-column building.'
 if profile=='horror':common+=' Actual documented mysteries only. Build tension through a concrete known clue, a contradiction, an unanswered question and the limits of the record. No invented ghosts, dialogue, witnesses, supernatural explanations or made-up evidence. Distinguish absence of evidence from proof.'
 if profile=='news':common+=' Show what was announced, what changes for a user, and what remains a proposal. Vary headline/product/workflow/comparison/takeaway shots. Any drawn interface must be labelled illustrative, not a genuine screenshot. Keep the narration concise; do not lengthen to fill a template.'
 if profile=='science':common+=' Science includes biology, chemistry, health, Earth science, physics and technology. Explain a mechanism using objects interacting and a visible before/after. Never use space as a default decorative world. A cell with a nucleus must not represent a bacterium. A surfactant head faces water, tail faces oil; no literal magnetic attraction claim.'
 if profile=='stickman':
  common=f'VISUAL IDENTITY {VERSION}: two large original unnamed stick figures in the supplied world. Write the story first; do not select Three.js objects or image-search queries. Each scene supplies visual_rationale, cause, attempt and consequence, describing actual actions involving the supported scenario props. Fixed stages are impact/experiment/escalation/fail/discovery/adapt/solution/twist. The stage metadata is assigned by the renderer and is never spoken.'
  common+=' Original What If story: a clear hypothetical rule, an immediate visible consequence, an attempted experiment, a failure caused by that same rule, a discovery, and a payoff. Each scene supplies cause/attempt/consequence; each follows causally from the preceding one. The solution stage means an outcome or realization, NOT a compulsory happy rescue or magic control panel. The premise may be impossible; consequences must be internally consistent and scientific qualifications honest. Two unnamed characters talk naturally and interact with the objects. No spoken Stickman/Arnold names or narrator repeating who did what. An impulsive attempt and a dry reaction create comedy; no explanatory lecture disguised as dialogue. First turn at most12 words. Do not invent numeric survival timelines. Reject a premise whose only novelty is an object becoming bigger or smaller without a compelling consequence. No recycling a competitor plot.'
 return common
def validate_director(draft,profile):
 if draft.get('director_version')!=VERSION:return # retain acknowledged older drafts without rewriting them
 scenes=draft.get('scenes',[])
 for s in scenes:
  if profile!='stickman' and (s.get('shot_type') not in SHOTS[profile] or s.get('hero_object') not in OBJECTS or s.get('object_motion') not in MOTIONS):raise ValueError('Unimplemented channel visual direction')
  if s.get('secondary_object','none') not in ('none',*OBJECTS) or s.get('interaction','none') not in ('none','approach','separate','encircle','transfer','contrast'):raise ValueError('Unsupported secondary object or interaction')
  if not 12<=len(s.get('visual_rationale',''))<=450:raise ValueError('A concrete shot action is required')
  q=s.get('image_query','')
  if len(q)>100 or '://' in q or '\n' in q:raise ValueError('Image direction must be a short entity query, not executable content or a URL')
  if profile=='stickman' and any(not s.get(k,'').strip() for k in ['cause','attempt','consequence']):raise ValueError('What If scene requires causal progression')
 if profile!='stickman' and len({s['shot_type'] for s in scenes})<3:raise ValueError('Use at least three distinct shot purposes, not a repeated diagram')
 if profile=='stickman' and scenes and scenes[0].get('turns') and len(scenes[0]['turns'][0]['text'].split())>12:raise ValueError('Start with a concise situation, not an opening lecture')
def authored_visual(story,row):
 profile=story['profile'];story['visual_identity']=identity(profile)
 if story.get('director_version')!=VERSION:return story
 for i,s in enumerate(story['scenes']):
  old=s.get('visual',{});s['visual']={**old,'shot_type':SHOTS[profile][i] if profile=='stickman' else s['shot_type'],'hero_object':s.get('hero_object','sphere'),'object_motion':s.get('object_motion','none'),'image_query':s.get('image_query',''),'visual_rationale':s['visual_rationale'],'secondary_object':s.get('secondary_object','none'),'interaction':s.get('interaction','none')}
 return story
def inferred_object(scene,story):
 text=(scene.get('narration','')+' '+scene.get('label','')).lower()
 if story['profile']=='history' and any(w in story.get('canonical_subject','').lower() for w in ('abu-simbel','abu_simbel','memphis','egypt')) and any(w in text for w in ('معبد','تمثال','temple','statue')):return 'egypt_temple'
 kicker=scene.get('visual',{}).get('kicker')
 known={'bubble':'surfactant','water-oil':'molecule','molecule':'surfactant','micelle':'micelle','rinse':'micelle','foam':'sphere'}
 if story['profile']=='science' and kicker in known:return known[kicker]
 families=[('bacterium',('بكتير','bacter')),('surfactant',('جزيء','صابون','surfactant')),('micelle',('مذيل','micelle','تجمعات')),('dna',('جين','وراث','dna')),('leaf',('نبات','ورقة','تمثيل ضوئي')),('heart',('قلب','شريان')),('cell',('خلي','cell')),('volcano',('بركان','volcano')),('rock_layers',('صخر','طبقات','أحفور')),('magnet',('مغناط','magnet')),('pendulum',('بندول','اهتزاز','pendulum')),('waveform',('صوت','موجة','sound')),('ship',('سفين','بحر','celeste','captain')),('temple',('معبد','أهرام','memphis','abu-simbel')),('monitor',('كود','codex','code','برمج')),('phone',('هاتف','موبايل')),('robot',('روبوت','ذكاء اصطناعي'))]
 # A micelle is the assembled structure, not an individual surfactant molecule.
 if any(x in text for x in ['مذيل','micelle','تجمعات دي']):return 'micelle'
 kind=next((kind for kind,words in families if any(w in text for w in words)),'document' if story['profile'] in ('history','horror') else 'molecule')
 if kind=='temple' and any(w in text for w in ('هرم','أهرام','pyramid')):return 'pyramid'
 if kind=='temple' and any(w in story.get('canonical_subject','').lower() for w in ('abu-simbel','abu_simbel','memphis','egypt')):return 'egypt_temple'
 return kind
def scene_plan(story):
 profile=story['profile'];result=[]
 for i,s in enumerate(story['scenes']):
  v=s.get('visual',{});kind=v.get('hero_object') or s.get('hero_object') or inferred_object(s,story)
  if kind not in OBJECTS:raise ValueError('Unsupported scene object')
  shot=v.get('shot_type') or s.get('shot_type') or SHOTS[profile][i%len(SHOTS[profile])]
  if profile=='stickman':shot=SHOTS[profile][i]
  query=v.get('image_query') or s.get('image_query') or ''
  if not query and profile in ('history','horror'):
   title=story.get('source',{}).get('title','');query=re.sub(r'[^a-zA-Z0-9 –-]',' ',title).strip()[:90]
  labels=s.get('labels') or v.get('labels') or []
  if profile=='news' and not labels:labels=[str(x) for x in (v.get('number'),v.get('detail'),s.get('label')) if x]
  result.append({'id':s['id'],'shot_type':shot,'hero_object':kind,'secondary_object':v.get('secondary_object') or s.get('secondary_object') or ('sphere' if profile=='science' and kind in ('surfactant','molecule') else 'none'),'interaction':v.get('interaction') or s.get('interaction') or ('approach' if profile=='science' and kind=='surfactant' else 'contrast' if profile=='science' and kind=='molecule' else 'none'),'object_motion':v.get('object_motion') or s.get('object_motion') or ['assemble','spin','flow','split','pulse','orbit','grow','drift'][i],'image_query':query,'visual_rationale':v.get('visual_rationale') or s.get('visual_rationale') or 'Illustration of the subject described in this exact scene; not original footage','labels':labels,'scenario':v.get('scenario'),'legacy_kind':v.get('kind'),'asset':v.get('asset'),'asset_label':v.get('asset_label')})
 return {'version':VERSION,'identity':identity(profile),'story_sha256':hashlib.sha256((json.dumps(story,ensure_ascii=False,indent=2)+'\n').encode()).hexdigest(),'scenes':result}
