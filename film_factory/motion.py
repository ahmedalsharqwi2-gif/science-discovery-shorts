"""Illustrative motion triggered by words actually present in the narration."""
import math,re
from PIL import Image,ImageDraw

LEX={
 'gas':r'غاز|الكربون|المتراكم',
 'waves':r'موج|بحر|المحيط|سفينة|سفينه',
 'lamp':r'منارة|مناره|المصباح|النور',
 'battle':r'معركة|معركه|جيش|جنود|حصار',
 'construction':r'بناء|مباني|المنازل|بنيت',
 'cell':r'خلية|خليه|خلايا|بكتيريا',
 'wave':r'موجات|اهتزاز|تردد|الصوت',
 'magnet':r'مغناطيس|مغناطيسي',
 'network':r'نموذج|ذكاء|بيانات|شريحة|شريحه|معالج|رقاقة',
}
def lexical_match(pattern,text):
 token=re.sub(r'[^\u0621-\u064a]','',str(text)).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))
 pattern=pattern.translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ة':'ه','ى':'ي'}))
 return re.fullmatch(r'(?:و|ف)?(?:ب|ل|ك)?(?:ال)?(?:'+pattern+r')',token) is not None

def events(words,profile):
 allowed={'horror':{'waves','lamp','gas'},'history':{'battle','construction','waves'},'science':{'cell','wave','magnet'},'news':{'network'}}[profile]
 result=[];last={}
 for word in words:
  for kind in allowed:
   if lexical_match(LEX[kind],word['text']) and word['start']-last.get(kind,-100)>9:
    last[kind]=word['start'];result.append({'kind':kind,'at':word['start'],'word':word['text']})
 return result
def draw(im,t,cues,accent):
 layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer);w,h=im.size
 for cue in cues:
  age=t-cue['at']
  if not 0<=age<5.5:continue
  a=int(190*min(1,age/.35)*min(1,(5.5-age)/.6));color=(*accent,a);kind=cue['kind']
  if kind=='gas':
   d.rounded_rectangle((160,650,920,1130),radius=25,fill=(4,15,24,210))
   d.polygon([(210,750),(360,1050),(650,1050),(780,750)],fill=(20,67,103,a),outline=color)
   for k in range(18):
    x=370+k*17;y=1020-((age*65+k*19)%240)
    d.ellipse((x-4,y-4,x+4,y+4),fill=(*accent,int(a*.7)))
   for k in range(3):
    x=760+age*16;y=790+k*65
    d.line((710,y,x,y+90),fill=color,width=4)
  elif kind=='waves':
   for row in range(4):
    pts=[(x,1150+row*45+math.sin(x/100-age*1.8+row)*22) for x in range(0,w+20,20)]
    d.line(pts,fill=color,width=3)
  elif kind=='lamp':
   cx,cy=540,720;angle=age*.65
   d.polygon([(cx,cy),(cx+math.cos(angle)*600,cy+math.sin(angle)*600),(cx+math.cos(angle+.18)*600,cy+math.sin(angle+.18)*600)],fill=(*accent,int(a*.17)))
   d.ellipse((cx-12,cy-12,cx+12,cy+12),fill=color)
  elif kind=='battle':
   for side in (-1,1):
    for k in range(7):
     x=540+side*(340-min(age,3)*65)+k%2*10;y=720+k*55
     d.rectangle((x-10,y-10,x+10,y+10),outline=color,width=3)
    x=540+side*(340-min(age,3)*65);d.line((x,690,x-side*90,690),fill=color,width=4)
    d.polygon([(x-side*90,690),(x-side*65,675),(x-side*65,705)],fill=color)
  elif kind=='construction':
   for k in range(7):
    x=200+k*100;rise=min(1,max(0,(age-k*.1)/.7));height=(100+k%3*70)*rise
    d.rectangle((x,1080-height,x+70,1080),outline=color,width=3)
  elif kind=='cell':
   for k in range(8):
    angle=k*math.tau/8;cx=540+200*math.cos(angle+age*.12);cy=870+200*math.sin(angle+age*.12);r=30+4*math.sin(age*2+k)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=color,width=3);d.ellipse((cx-7,cy-7,cx+7,cy+7),fill=color)
  elif kind=='wave':
   d.line([(x,850+90*math.sin(x/65-age*3)) for x in range(140,950,5)],fill=color,width=4)
  elif kind=='magnet':
   for k in range(4):d.arc((300-k*30,700-k*25,780+k*30,1050+k*25),0,360,fill=color,width=3)
  elif kind=='network':
   for k in range(9):
    angle=k*math.tau/9;cx=540+240*math.cos(angle);cy=850+180*math.sin(angle)
    d.line((540,850,cx,cy),fill=(*accent,int(a*.45)),width=2)
    p=(age*.7+k/9)%1;x=540+(cx-540)*p;y=850+(cy-850)*p
    d.ellipse((cx-12,cy-12,cx+12,cy+12),outline=color,width=3);d.ellipse((x-6,y-6,x+6,y+6),fill=color)
 im.alpha_composite(layer)
