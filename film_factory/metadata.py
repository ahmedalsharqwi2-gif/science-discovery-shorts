"""Topic-specific public titles, captions and hashtags; no transcript dumps."""
import json,re
from pathlib import Path
BRANDS={'horror':'ملفات غامضه','history':'نقص ونروى','science':'اسرار الكون','news':'ai على السريع'}
BASE={'horror':['ملفات_غامضه','قصص_حقيقية','غموض'],'history':['نقص_ونروى','تاريخ','قصص_تاريخية'],'science':['اسرار_الكون','علوم','اكتشافات'],'news':['ai_على_السريع','ذكاء_اصطناعي','اخبار_التقنية']}
def create(plan,profile):
 if profile=='horror' and (plan.get('fiction') is not False or not plan.get('documented')):raise ValueError('Fiction can never be published as a true horror story')
 source=plan.get('source',{});url=source.get('url','')
 if not url.startswith('https://'):raise ValueError('A real source URL is required')
 if plan.get('editorial_review',{}).get('supported') is not True:raise ValueError('Editorial review must approve before publication')
 title=re.sub(r'\s+',' ',plan['title']).strip();brand=BRANDS[profile]
 if not title.startswith(brand):title=brand+' | '+title
 title=title[:100].rstrip(' |،')
 tags=list(BASE[profile]);raw=[plan['title']]+[x for scene in plan['scenes'] for x in scene.get('labels',[])]
 for label in raw[1:]:
  tag=re.sub(r'[^\w\u0621-\u064a\s]','',label).strip().replace(' ','_')
  if 2<=len(tag)<=28 and tag not in tags:tags.append(tag)
  if len(tags)>=7:break
 disclosure='واقعة موثقة؛ الصور والمؤثرات إعادة بناء توضيحية وليست تسجيلًا للواقعة.' if profile=='horror' else 'صور مولّدة وموشن للتوضيح؛ المعلومات من المصدر.'
 if profile=='news':disclosure+=' التعليق الكوميدي للتسلية.'
 caption=title+'\n\n'+disclosure+'\nالمصدر: '+source.get('publisher','')+'\n'+url+'\n\n'+' '.join('#'+tag for tag in tags)
 result={'title':title,'caption':caption,'description':caption,'hashtags':['#'+x for x in tags],'tags':tags,'series':brand,'source_url':url,'source_type':'documented','fiction':False,'generated_illustrations':True,'containsSyntheticMedia':True}
 Path('output').mkdir(exist_ok=True);Path('output/publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
