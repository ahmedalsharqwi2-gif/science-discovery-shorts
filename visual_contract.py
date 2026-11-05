"""Locked channel contract. Invalid configuration is a production error."""
import json,re,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SUPPORTED_VERSIONS={1}
BANNED_OPENINGS=("أهلا","أهلاً","النهاردة","في الفيديو","هنشوف","هنتكلم","موضوع النهاردة","هل تعلم","في حلقة النهاردة")
def load_template(path=None):
 p=Path(path) if path is not None else ROOT/'config/visual_template.json'
 v=json.loads(p.read_text(encoding='utf8'))
 if type(v.get('version')) is not int or v['version'] not in SUPPORTED_VERSIONS:raise ValueError('Unknown visual template version')
 if not v.get('locked') or not isinstance(v.get('safe_zone'),dict):raise ValueError('Locked safe_zone required')
 z=v['safe_zone']
 for k in ('text_x','text_y','text_x_lower','art_stage','caption_y_bottom','caption_center_x','caption_max_width','caption_max_height','chrome_min_y'):
  if k not in z:raise ValueError('Missing safe-zone field: '+k)
 if v['canvas']!={'w':1080,'h':1920,'fps':30}:raise ValueError('Channel canvas must remain 1080x1920/30fps')
 if not v.get('display_name') or not all(re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in v['palette'].values()):raise ValueError('Invalid identity')
 identity=json.loads((ROOT/'config/channel_identity.json').read_text())
 if identity['name']!=v['display_name'] or identity.get('schedule_and_publication_configuration_changed') is not False:raise ValueError('Channel identity mismatch or publication configuration changed')
 for source,target in [('background','bg'),('ink','ink'),('accent','accent')]:
  if identity[source].lower()!=v['palette'][target].lower():raise ValueError('Identity palette conflict: '+target)
 return v

def assert_in_safe_zone(name,bbox,*,kind='text',template=None):
 t=template or load_template();z=t['safe_zone']
 if kind not in ('text','chrome'):raise ValueError('Unknown text kind')
 if len(bbox)!=4 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in bbox):raise ValueError('Finite bounding box required')
 x0,y0,x1,y1=bbox
 if not(x0<x1 and y0<y1):raise ValueError('Empty/reversed bounding box')
 lo=z['chrome_min_y'] if kind=='chrome' else z['text_y'][0]
 if x0<z['text_x'][0] or x1>z['text_x'][1] or y0<lo or y1>z['text_y'][1]:raise ValueError(name+' leaves the safe text zone')
 lower=z['text_x_lower']
 if y1>=lower['from_y'] and (x0<lower['x'][0] or x1>lower['x'][1]):raise ValueError(name+' enters the lower action column')
 if kind=='text' and y1>t['safe_zone']['art_stage']['focal_y'][1] and name!='caption':raise ValueError('Only captions may occupy the bottom text band')
 return tuple(bbox)

def overlaps(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def validate_scene_boxes(title,caption,focal,*,scale,template=None):
 t=template or load_template()
 for n,b in [('title',title),('caption',caption)]:
  if b:assert_in_safe_zone(n,b,template=t)
 if not math.isfinite(scale) or scale<t['safe_zone']['art_stage']['min_scale_vs_reference']:raise ValueError('Focal subject is too small')
 if focal and any(b and overlaps(b,focal) for b in (title,caption)):raise ValueError('Text covers the focal subject')
 return True

def validate_accent(title,word,*,prefix='',colored_words=None):
 if not isinstance(word,str) or len(word.split())!=1 or word not in title:raise ValueError('Exactly one literal accent word required')
 authored=title[len(prefix):] if prefix and title.startswith(prefix) else title
 if word not in authored or authored.split().count(word)!=1:raise ValueError('Accent word must occur exactly once outside the prefix')
 if colored_words is not None and list(colored_words)!=[word]:raise ValueError('Exactly one word may be coloured')
 return word

def validate_hook(line,*,max_words,profile,source_terms=()):
 if not isinstance(line,str):raise ValueError('Hook must be text')
 line=' '.join(line.split())
 if not line or len(line.split())>max_words:raise ValueError('Empty/over-length hook')
 clean=re.sub(r'[ًٌٍَُِّْٰ]','',line)
 if any(clean.startswith(re.sub(r'[ًٌٍَُِّْٰ]','',x)) for x in BANNED_OPENINGS):raise ValueError('Banned hook opening')
 number=bool(re.search(r'[0-9٠-٩]',line));neg=bool(re.search(r'(?:^|\s)(?:مش|مفيش|محدش|لم|لن|لا|مافيش)(?:\s|$)',line));conditional=bool(re.search(r'(?:^|\s)لو(?:\s|$)',line));decisive=any(v in line for v in ('وقّفت','وقفت','سحبت','شالت','رفعت'));named=any(w and w in line for w in source_terms)
 if not(number or neg or conditional or named or (profile=='news' and decisive)):raise ValueError('Hook needs a sourced concrete fact, number, negation or contradiction')
 if profile=='stickman' and (clean.startswith(('تخيل معايا','استعد')) or not(number or neg or conditional)):raise ValueError('What-if hook must state the conditional result')
 if profile=='horror' and (any(w in clean for w in ('رعب','مخيف','ملفات غامضة')) or re.search(r'(?:^|\s)(?:أنت|انت|إنت|إنتي|إنتوا)(?:\s|$)',clean)):raise ValueError('Unsupported horror hook register')
 if profile=='science' and (re.match(r'^\S+\s+(?:هو|هي|عبارة|يعني)(?:\s|$)',clean) or any(clean.startswith(w+' ') for w in source_terms if w)):raise ValueError('Science hook cannot be a definition or open with the topic name')
 if profile=='history' and 'نقص ونروي' in line:raise ValueError('Brand is not a hook')
 if profile=='news' and (not(number or decisive) or 'من أخبار الأسبوع:' in line):raise ValueError('News hook needs a figure or decisive verb, not the brand prefix')
 return line

def require_source_support(hook,quote,source_text,review):
 if not quote or quote not in source_text or review.get('supported') is not True:raise ValueError('Source-backed hook review required before scene generation')
 return hook
