"""A photographic world, spatial reveals and diagrams tied to actual speech."""
import math
from PIL import Image,ImageDraw,ImageOps
from film_factory.motion import events,draw as semantic_motion
from film_factory.render import W,H,txt,para,lines,INK,MUTED,Renderer

COLORS={'horror':(193,143,121),'history':(245,177,92),'science':(72,216,239)}

class FilmRenderer(Renderer):
 def __init__(self,plan,timing,images):
  # Reuse the tested encoder, but avoid rendering any obsolete motion cards.
  self.plan=plan;self.t=timing;self.duration=timing['duration'];self.photos=[];self.captions=[];self.motion_events=events(timing['words'],plan['profile'])
  if len(images)!=len(timing['scenes']):raise ValueError('Every spoken scene needs one generated photograph')
  for path in images:
   with Image.open(path) as im:self.photos.append(ImageOps.fit(im.convert('RGB'),(1188,2112),centering=(.5,.48)))
  self.shade=Image.new('RGBA',(W,H));d=ImageDraw.Draw(self.shade)
  for y in range(H):
   alpha=int(255*max(max(0,1-y/500)*.86,max(0,(y-1160)/760)*.97))
   d.line((0,y,W,y),fill=(3,6,12,alpha))
  words=timing['words']
  groups=timing.get('caption_groups') or [{'text':' '.join(x['text'] for x in words[i:i+5]),'start':words[i]['start'],'end':words[min(i+4,len(words)-1)]['end']} for i in range(0,len(words),5)]
  for group in groups:
   panel=Image.new('RGBA',(960,235));d=ImageDraw.Draw(panel)
   d.rounded_rectangle((0,0,959,234),radius=24,fill=(4,9,16,225))
   para(panel,group['text'],480,73,48,880,maxlines=2)
   self.captions.append((group['start'],group['end'],panel))
 def frame(self,t):
  index=next((i for i,s in enumerate(self.t['scenes']) if s['start']<=t<s['end']),len(self.photos)-1)
  s=self.t['scenes'][index];profile=self.plan['profile'];accent=COLORS[profile]
  u=max(0,min(1,(t-s['start'])/(s['end']-s['start'])));ease=u*u*(3-2*u)
  breath=(math.sin(t*3.7)*2 if profile=='horror' else 0)
  z=1.025+.055*(ease if index%2==0 else 1-ease);cw,ch=W/z,H/z
  cx=594+25*math.sin(index+ease*1.6)+breath;cy=1056+24*math.cos(index+ease)+breath
  im=self.photos[index].crop((round(cx-cw/2),round(cy-ch/2),round(cx+cw/2),round(cy+ch/2))).resize((W,H),Image.Resampling.BICUBIC).convert('RGBA')
  age=t-s['beat'];d=ImageDraw.Draw(im)
  if profile=='horror':
   # A single moving pool of light reveals the photograph; no rapid strobe.
   light=Image.new('RGBA',(W,H),(0,0,0,0));ld=ImageDraw.Draw(light)
   sweep=540+170*math.sin(t*.22);ld.polygon([(int(sweep),560),(int(sweep-230),1430),(int(sweep+260),1430)],fill=(200,205,170,15));im.alpha_composite(light)
   if self.plan.get('fiction') is True and age>=0 and s['effect'] in ('latch','footsteps'):
    shadow=Image.new('RGBA',(W,H));sd=ImageDraw.Draw(shadow);alpha=round(42*min(1,age/1.5));x=1000-int(min(1,age/2)*180)
    sd.ellipse((x-110,570,x+80,860),fill=(0,0,0,alpha));sd.polygon([(x-70,810),(x+60,810),(x+170,1500),(x-150,1500)],fill=(0,0,0,alpha));im.alpha_composite(shadow)
  elif profile=='history' and s['effect']=='embers' and age>=0:
   for k in range(26):
    x=(k*139+math.sin(t*.7+k)*40)%W;y=1450-((t*70+k*81)%1050);r=2+k%3
    d.ellipse((x-r,y-r,x+r,y+r),fill=(255,150+k%80,40,140))
  elif profile=='history' and s['effect']=='firebreak' and age>=0:
   a=min(1,age/.7);d.rounded_rectangle((450,630,630,1300),radius=20,fill=(15,18,22,int(100*a)),outline=accent,width=3)
   txt(im,'فاصل بين المباني',(540,1380),35,accent)
  elif profile=='science' and s['effect'] in ('orbit','fall') and age>=0:
   # Explanatory overlay, not fictitious measured instrument data.
   panel=Image.new('RGBA',(820,630));pd=ImageDraw.Draw(panel);pd.rounded_rectangle((0,0,819,629),radius=32,fill=(3,12,23,170))
   if s['effect']=='orbit':
    pd.ellipse((165,90,655,580),outline=(90,170,210,150),width=3);pd.ellipse((330,255,490,415),fill=(30,88,137),outline=accent,width=3)
    a=(age*.45)%math.tau;x=410+245*math.cos(a);y=335+245*math.sin(a);pd.ellipse((x-16,y-16,x+16,y+16),fill=accent)
    pd.line((x,y,410,335),fill=(250,180,85),width=4);txt(panel,'سقوط مستمر حول الأرض',(410,47),34)
   else:
    y=100+(age%2.2)/2.2*360
    for x,r in [(280,35),(510,20)]:pd.ellipse((x-r,y-r,x+r,y+r),outline=accent,width=4);pd.line((x,y+r+15,x,y+r+95),fill=accent,width=4)
    txt(panel,'بيسقطوا مع بعض',(410,550),38)
   im.alpha_composite(panel,(130,540))
  semantic_motion(im,t,self.motion_events,accent)
  # Brief editorial focus changes every few seconds, without covering captions.
  cut=int((t-s['start'])/4.5)
  if cut%2:
   im=im.resize((1124,1998),Image.Resampling.BICUBIC).crop((22,39,1102,1959))
  im.alpha_composite(self.shade);d=ImageDraw.Draw(im)
  d.rounded_rectangle((60,90,1020,208),radius=25,fill=(4,9,16,210),outline=accent,width=2)
  txt(im,self.plan['series'],(540,150),52,accent)
  if profile!='horror':para(im,s['title'],540,300,50,930,maxlines=2)
  else:para(im,self.plan['title'] if t<6 else 'واقعة موثقة • إعادة بناء بصرية',540,270,34,920,maxlines=2)
  # Horror avoids information cards which would break immersion.
  if profile!='horror':
   for k,label in enumerate(s['labels']):
    if t>=s['label_beats'][k]:
     panel=Image.new('RGBA',(960,93));pd=ImageDraw.Draw(panel);pd.rounded_rectangle((0,0,959,92),radius=20,fill=(4,13,23,210),outline=accent,width=2);para(panel,label,480,25,34,880,maxlines=2);im.alpha_composite(panel,(60,1240+k*104))
  for start,end,panel in self.captions:
   if start<=t<end:im.alpha_composite(panel,(60,1490));break
  footer='صور ومؤثرات مولّدة للتوضيح • واقعة موثقة' if profile=='horror' else 'مشاهد مولّدة للتوضيح • المعلومات من المصدر'
  txt(im,footer,(540,1770),26,MUTED)
  txt(im,self.plan['source']['publisher'],(540,1820),25,MUTED)
  d=ImageDraw.Draw(im);d.line((60,1870,1020,1870),fill=(34,43,53),width=5);d.line((60,1870,60+960*t/self.duration,1870),fill=accent,width=5)
  return im.convert('RGB')
