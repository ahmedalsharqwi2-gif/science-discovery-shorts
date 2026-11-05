"""Balance scientific subjects without blocking an otherwise available new topic."""
from collections import Counter
DOMAINS={
 'medicine':('antibiotic','disease','vaccine','health','مرض','مضاد','لقاح','صحة'),
 'biology':('bacteria','microb','dna','gene','plant','animal','بكتير','خلية','جين','نبات','حيوان'),
 'chemistry':('chemistry','chemical','soap','molecule','reaction','كيمي','صابون','جزيء','تفاعل'),
 'earth':('climate','ocean','earthquake','volcano','geology','مناخ','محيط','زلزال','بركان','جيولوج'),
 'computing':('artificial intelligence','computer','software','algorithm','حاسو','برمج','خوارزم','ذكاء اصطناعي'),
 'engineering':('engineer','battery','robot','material','هندس','بطارية','روبوت','مادة'),
 'physics':('physics','quantum','magnet','sound','light','energy','فيزي','كمومي','مغناط','صوت','ضوء','طاقة'),
 'astronomy':('space','nasa','astronom','galaxy','planet','black hole','فضاء','ناسا','فلك','مجرة','كوكب','ثقب أسود')}
def domain(row):
 selection=row.get('source_selection');selection=selection if isinstance(selection,dict) else {}
 selected=row.get('science_domain') or selection.get('science_domain')
 if selected in DOMAINS:return selected
 source=row.get('source') or {};url=source if isinstance(source,str) else source.get('url','') if isinstance(source,dict) else ''
 text=' '.join(str(row.get(k,'')) for k in ('title','canonical_subject','topic_key','publisher','url'))+' '+url;text=text.lower()
 return next((name for name,words in DOMAINS.items() if any(w in text for w in words)),'general')
def balanced(rows,history):
 recent=[domain(r) for r in history[-14:]];counts=Counter(recent);last=set(recent[-2:]);ranked=[]
 for i,row in enumerate(rows):
  category=domain(row);score=counts[category]+(2 if category in last else 0)+(.3 if category=='astronomy' else 0)
  ranked.append((score,i,{**row,'science_domain':category}))
 return [r for _,_,r in sorted(ranked,key=lambda x:(x[0],x[1]))]
