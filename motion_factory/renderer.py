"""Deterministic time-based diagrams, Arabic typography and measured captions.

Uses the Motion Kit's time -> frame approach, not its unrelated English demo.
No downloaded photographs, generated stock backgrounds, or random scene fallbacks.
"""
import math
import subprocess
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features

W, H = 1080, 1920
INK = (238, 231, 211)
MUTED = (152, 164, 168)
COLORS = {'science': (94, 210, 195), 'history': (226, 152, 87),
          'horror': (130, 179, 173), 'news': (122, 183, 239)}


@lru_cache(maxsize=64)
def font(size):
    root = Path(__file__).resolve().parent.parent
    candidates = [root/'assets/NotoSansArabic-Bold.ttf', root/'photo_motion/assets/NotoSansArabic-Bold.ttf']
    path = next((p for p in candidates if p.is_file()), None)
    if path is None or not features.check('raqm'):
        raise RuntimeError('Noto Sans Arabic and Pillow RAQM are required')
    return ImageFont.truetype(str(path), size)


def text(draw, value, xy, size=38, color=INK, width=920):
    value = str(value)
    while size > 20 and draw.textlength(value, font=font(size), direction='rtl') > width:
        size -= 2
    if draw.textlength(value, font=font(size), direction='rtl') > width:
        raise ValueError('Text does not fit the safe area')
    draw.text(xy, value, font=font(size), fill=color, anchor='mm', direction='rtl')


def wrap(draw, value, size=42, width=900):
    rows = ['']
    for word in value.split():
        test = (rows[-1]+' '+word).strip()
        if draw.textlength(test, font=font(size), direction='rtl') > width:
            rows.append(word)
        else:
            rows[-1] = test
    return rows


def lerp(a, b, p):
    return tuple(round(x+(y-x)*p) for x, y in zip(a, b))


class MotionRenderer:
    def __init__(self, plan, timing, preview=False):
        self.plan, self.timing = plan, timing
        self.duration = float(timing['duration'])
        self.scenes = timing['scenes']
        if self.duration <= 0 or not self.scenes:
            raise ValueError('Missing scene timing')
        self.accent = COLORS[plan['profile']]
        self.preview = preview
        self.captions = []
        groups = timing.get('caption_groups')
        if groups:
            self.captions = [(g['start'], g['end'], g.get('text', '')) for g in groups]
        else:
            words = timing.get('words', [])
            for i in range(0, len(words), 7):
                group = words[i:i+7]
                self.captions.append((group[0]['start'], group[-1]['end'], ' '.join(w['text'] for w in group)))

    def octopus(self, d, t, kind):
        cx, cy = 540, 790
        phase = .5+.5*math.sin(t*.8)
        col = lerp((221, 104, 55), (120, 109, 210), phase)
        if kind == 'camouflage':
            for k in range(12):
                x=150+k*67; y=1120+20*math.sin(k)
                d.ellipse((x-65, y-35, x+65, y+35), fill=lerp((31, 56, 48), col, .2))
        for k in range(8):
            angle = math.pi*(.12+.76*k/7)
            pts=[]
            for n in range(45):
                s=n/44; x=cx+math.cos(angle)*s*380
                y=cy+110+s*240+math.sin(s*6+t*1.5+k)*s*55
                pts.append((x,y))
            d.line(pts, fill=tuple(int(v*.3) for v in col), width=45)
            d.line(pts, fill=col, width=23)
            for x,y in pts[::5]:d.ellipse((x-5,y-5,x+5,y+5), fill=INK)
        d.ellipse((390,575,690,940), fill=(29,42,46), outline=col, width=6)
        for k in range(38):
            a=k*2.399; r=math.sqrt(k/38)*130
            x=cx+math.cos(a)*r; y=760+math.sin(a)*r*1.16
            size=4+8*(.5+.5*math.sin(t*2+k))
            c=(col,(219,165,59),(94,177,168))[k%3]
            d.ellipse((x-size,y-size,x+size,y+size),fill=c)
        for x in (500,580):
            d.ellipse((x-15,837,x+15,879),fill=INK)
            d.ellipse((x-5,852,x+7,873),fill=(12,18,22))
        if kind == 'nerve':
            for k in range(8):
                x=200+k*97; p=(t*.6+k*.12)%1
                d.line((540,530,x,1040),fill=(42,75,74),width=2)
                px=540+(x-540)*p;py=530+510*p
                d.ellipse((px-7,py-7,px+7,py+7),fill=self.accent)
        if kind == 'pigment':
            d.ellipse((340,1050,740,1380),fill=(17,27,31),outline=self.accent,width=3)
            r=35+70*phase
            d.ellipse((540-r,1215-r,540+r,1215+r),fill=col)
            for k in range(10):
                a=k*math.tau/10
                d.line((540+math.cos(a)*r,1215+math.sin(a)*r,540+math.cos(a)*150,1215+math.sin(a)*150),fill=self.accent,width=3)
            text(d,'تكبير توضيحي لكيس الصبغة',(540,1430),30)

    def layers(self, d, t):
        science=self.plan['profile']=='science'
        labels=['السطح','الصبغة','انعكاس الضوء'] if science else ['سطح البحيرة','مياه أعمق','تراكم الغاز']
        for i, label in enumerate(labels):
            y=620+i*210
            d.polygon([(150,y),(800,y-50),(930,y+80),(270,y+130)],
                      fill=(26+i*7,57+i*8,65+i*5),outline=self.accent,width=3)
            for k in range(14):
                x=290+k*34;y2=y+30+18*math.sin(k*.8+t*(1+i*.2))
                r=6+(i==1)*5
                d.ellipse((x-r,y2-r,x+r,y2+r),fill=self.accent)
            text(d,label,(540,y+150),32)
        text(d,'مقطع مبسط ، الرسم مش بمقياس',(540,1340),28,MUTED)

    def canal(self,d,t,kind,index):
        # Explicit schematic: no fabricated geospatial precision.
        d.polygon([(120,650),(460,620),(515,830),(430,1010),(220,1280),(120,1140)],fill=(29,50,53))
        d.polygon([(615,650),(940,690),(950,1160),(720,1290),(650,980)],fill=(29,50,53))
        d.rounded_rectangle((150,510,930,620),radius=40,fill=(25,65,82))
        d.polygon([(475,1040),(600,1010),(830,1440),(690,1470)],fill=(25,65,82))
        text(d,'البحر المتوسط',(540,560),32)
        text(d,'البحر الأحمر',(740,1400),30)
        text(d,'مصر',(300,920),42)
        text(d,'سيناء',(790,900),36)
        route=[(540,620),(545,800),(550,1010),(680,1280)]
        d.line(route,fill=(58,100,113),width=20)
        if kind=='excavation':
            length=int(3*min(1,(t%6)/4))+1
            d.line(route[:max(2,length)],fill=self.accent,width=9)
            for k in range(6):
                x=320+k*72;y=1150+9*math.sin(t*3+k)
                d.ellipse((x-9,y-35,x+9,y-17),fill=INK)
                d.line((x,y-17,x,y+18),fill=INK,width=4)
                d.line((x,y,x+25,y+15+math.sin(t*4)*10),fill=self.accent,width=4)
        else:
            d.line(route,fill=self.accent,width=8)
            p=(t*.12)%1; y=660+p*520;x=545+max(0,p-.6)*230
            d.polygon([(x-20,y-32),(x+20,y-32),(x+26,y+18),(x,y+40),(x-26,y+18)],fill=INK)
        if kind=='route':
            d.arc((80,780,965,1580),0,170,fill=(86,103,106),width=4)
            text(d,'مسار توضيحي',(540,1490),28,MUTED)
        text(d,'خريطة تخطيطية ، ليست للملاحة',(540,1550),28,MUTED)

    def lake(self,d,t,kind):
        d.polygon([(100,890),(280,600),(435,820),(690,680),(950,890),(950,1130),(100,1130)],fill=(30,51,48),outline=self.accent)
        d.ellipse((190,820,890,1050),fill=(22,59,72),outline=self.accent,width=3)
        for k in range(5):
            r=40+(t*25+k*48)%280
            d.ellipse((540-r,935-r*.13,540+r,935+r*.13),outline=(47,88,99),width=2)
        d.polygon([(140,1130),(420,1370),(720,1300),(940,1130)],fill=(33,44,40))
        if kind in ('gas','valley'):
            # Arrows are labelled illustrations, never a visible poisonous cloud.
            text(d,'أسهم تفسيرية لغاز غير مرئي',(540,580),32)
            for k in range(5):
                p=(t*.25+k*.18)%1;x=300+p*450;y=1040+p*280
                d.line((x-30,y-22,x+20,y+20),fill=self.accent,width=4)
                d.polygon([(x+20,y+20),(x,y+16),(x+17,y-1)],fill=self.accent)
        if kind=='pipe':
            d.line((570,1020,570,720),fill=INK,width=14)
            for k in range(9):
                y=1020-((t*90+k*37)%320)
                d.ellipse((562,y-6,578,y+6),fill=self.accent)
            text(d,'تنفيس تدريجي',(540,1250),36)
        text(d,'رسم تفسيري ، مش تصوير للحادثة',(540,1510),29,MUTED)

    def network(self,d,t,kind,labels=()):
        if kind=='comparison':
            for i in range(2):
                x=140+i*440
                d.rounded_rectangle((x,650,x+360,1160),radius=22,outline=self.accent,width=3)
                for k in range(4):
                    y=760+k*85
                    d.ellipse((x+50,y-8,x+66,y+8),fill=self.accent)
                    d.line((x+85,y,x+290,y),fill=(61,88,99),width=3)
                    if k==int(t/2)%4:
                        d.rounded_rectangle((x+28,y-24,x+320,y+24),radius=10,outline=self.accent,width=4)
                label=labels[i] if i<len(labels) else ('فكرة' if i==0 else 'فكرة تانية')
                text(d,label,(x+180,1080),30,width=300)
            text(d,'مقارنة مفاهيمية ، ليست نتائج أداء',(540,1310),30,MUTED)
            return
        d.rounded_rectangle((405,760,675,1030),radius=22,fill=(26,42,56),outline=self.accent,width=5)
        text(d,'AI',(540,890),70)
        for k in range(8):
            a=k*math.tau/8;x=540+330*math.cos(a);y=890+330*math.sin(a)
            d.line((540,890,x,y),fill=(52,79,99),width=3)
            d.ellipse((x-20,y-20,x+20,y+20),outline=self.accent,width=4)
            p=(t*.5+k*.15)%1;px=540+(x-540)*p;py=890+(y-890)*p
            d.ellipse((px-7,py-7,px+7,py+7),fill=INK)
        text(d,'شرح تخطيطي ، بدون أرقام أداء مختلقة',(540,1390),28,MUTED)

    def timeline(self,d,t,profile):
        labels = ['١٨٥٩','١٨٦٩','١٩٥٦'] if profile=='history' else ['المصدر','التطوير','المراجعة']
        d.line((160,920,920,920),fill=(69,77,77),width=6)
        for i,label in enumerate(labels):
            x=180+i*360;r=14+5*math.sin(t*2-i)
            d.ellipse((x-r,920-r,x+r,920+r),fill=self.accent)
            text(d,label,(x,1010),38,width=300)
        text(d,'محطات منفصلة ، مش فواصل زمنية بمقياس',(540,1230),28,MUTED)

    def frame(self,t):
        im=Image.new('RGB',(W,H),(17,21,25));d=ImageDraw.Draw(im)
        for x in range(60,W,120):d.line((x,330,x,1590),fill=(23,29,32))
        for y in range(400,1590,120):d.line((70,y,1010,y),fill=(23,29,32))
        d.rectangle((35,35,1045,1885),outline=(48,55,58),width=2)
        text(d,self.plan['series'],(540,115),38)
        d.line((70,180,1010,180),fill=(54,61,63),width=2)
        index=next((i for i,s in enumerate(self.scenes) if s['start']<=t<s['end']),len(self.scenes)-1)
        s=self.scenes[index];local=max(0,t-s['start']);kind=s['kind'];profile=self.plan['profile']
        action=max(0,t-float(s.get('beat',s['start'])))
        text(d,'المشهد '+str(index+1),(150,240),26,MUTED,width=220)
        title_y=340+round(35*(1-min(1,local/.6))**3)
        text(d,s['title'],(540,title_y),58)
        if kind in ('octopus','pigment','nerve','camouflage'):self.octopus(d,action,kind)
        elif kind=='layers':self.layers(d,action)
        elif kind in ('canal','route','excavation'):self.canal(d,action,kind,index)
        elif kind in ('lake','gas','valley','pipe'):self.lake(d,action,kind)
        elif kind=='timeline':self.timeline(d,action,profile)
        elif kind in ('network','chip','comparison','flow'):self.network(d,action,kind,s.get('labels',[]))
        else:raise ValueError('Unsupported scene kind: '+kind)
        caption=next((v for a,b,v in self.captions if a<=t<b),'')
        if self.preview:caption='معاينة حركة صامتة ، ليست الفيديو النهائي'
        rows=wrap(d,caption,size=40)
        if len(rows)>3:raise ValueError('Caption exceeds mobile safe area')
        for i,row in enumerate(rows):text(d,row,(540,1650+i*65),40)
        d.line((70,1800,1010,1800),fill=(59,66,67),width=4)
        d.line((70,1800,70+940*min(1,t/self.duration),1800),fill=self.accent,width=5)
        text(d,self.plan['source']['publisher'],(540,1850),23,MUTED,width=900)
        return im

    def encode(self,path,width=1080,fps=30):
        if width not in (360,540,1080):raise ValueError('Unsupported output width')
        height=width*16//9
        proc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24',
            '-s',f'{width}x{height}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast',
            '-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
        try:
            for i in range(math.ceil(self.duration*fps)):
                frame=self.frame(i/fps)
                if width!=W:frame=frame.resize((width,height),Image.Resampling.LANCZOS)
                proc.stdin.write(frame.tobytes())
            proc.stdin.close()
            if proc.wait()!=0:raise RuntimeError('Motion encoding failed')
        except BaseException:
            proc.kill();proc.wait();raise
