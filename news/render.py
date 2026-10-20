"""1080x1920 native motion cards; Arabic shaping, mobile safe area, measured captions."""
import json, math, re, subprocess
from pathlib import Path
from difflib import SequenceMatcher
import numpy as np
from PIL import Image,ImageDraw,ImageFont
W,H,FPS=1080,1920,30
BG=(7,14,31);CYAN=(65,223,233);GOLD=(255,185,82);INK=(237,244,255);MUTED=(148,168,195)
FONT=Path(__file__).resolve().parent.parent/'assets/NotoSansArabic-Bold.ttf'
REG=FONT.with_name('NotoSansArabic-Regular.ttf')
def font(size,bold=True):return ImageFont.truetype(str(FONT if bold else REG),size)
def textfont(text,size,bold=True):
    if re.search(r'[A-Za-z/•]',str(text)):
        path='/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf'
        return ImageFont.truetype(path,size)
    return font(size,bold)
def txt(im,text,xy,size=42,fill=INK,anchor='mm',bold=True):
    ImageDraw.Draw(im).text(xy,str(text),font=textfont(text,size,bold),fill=fill,anchor=anchor,direction='rtl')
def lines(text,size,width):
    d=ImageDraw.Draw(Image.new('RGB',(2,2)));out=[];line=''
    for word in str(text).split():
        test=(line+' '+word).strip()
        if d.textlength(test,font=textfont(test,size),direction='rtl')>width and line:out.append(line);line=word
        else:line=test
    if line:out.append(line)
    return out

def para(im,text,cx,y,size=44,width=880,fill=INK,maxlines=3):
    rows=lines(text,size,width)
    if len(rows)>maxlines:
        size=max(27,size-7);rows=lines(text,size,width)
    if len(rows)>maxlines:raise ValueError('Arabic text exceeds mobile card bounds')
    for i,row in enumerate(rows):txt(im,row,(cx,y+i*(size*1.6)),size,fill)

def norm(w):return re.sub(r'[^\u0621-\u064a0-9]','',re.sub(r'[\u064b-\u065fـ]','',w)).translate(str.maketrans({'أ':'ا','إ':'ا','آ':'ا','ى':'ي','ة':'ه'}))

def align(plan,wav):
    from faster_whisper import WhisperModel
    model=WhisperModel('small',device='cpu',compute_type='int8',cpu_threads=4)
    segs,_=model.transcribe(str(wav),language='ar',word_timestamps=True,beam_size=5,vad_filter=False)
    actual=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in segs for w in s.words or [] if norm(w.word)]
    expected=plan['narration'].split();matcher=SequenceMatcher(None,[norm(w) for w in expected],[norm(w['text']) for w in actual],autojunk=False);anchors={}
    for b in matcher.get_matching_blocks():
        for k in range(b.size):anchors[b.a+k]=actual[b.b+k]
    coverage=len(anchors)/max(1,len(expected))
    if coverage<.65:raise ValueError(f'Insufficient measured Arabic timing anchors ({coverage:.1%}); retained audio for review')
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]))
    def at(index):
        if index in anchors:return anchors[index]['start']
        left=max([i for i in anchors if i<index],default=None);right=min([i for i in anchors if i>index],default=None)
        if left is None:return 0.
        if right is None:return anchors[left]['end']
        return anchors[left]['start']+(anchors[right]['start']-anchors[left]['start'])*(index-left)/(right-left)
    words=[{'text':w,'start':at(i),'end':at(i+1) if i+1<len(expected) else duration,'measured':i in anchors} for i,w in enumerate(expected)]
    cursor=0;scenes=[]
    for scene in plan['scenes']:
        count=len(scene['narration'].split());start=at(cursor) if cursor else 0;cursor+=count
        end=at(cursor) if cursor<len(expected) else duration
        if end-start<2:raise ValueError('A scene has insufficient actual speech time')
        scenes.append({**scene,'start':start,'end':end})
    if actual and duration-actual[-1]['end']>2.5:raise ValueError('Unexpected long trailing silence; review final spoken sentence')
    result={'coverage':coverage,'duration':duration,'words':words,'scenes':scenes,'asr_words':actual,'interpolated_words':[i for i in range(len(words)) if i not in anchors]}
    Path('output/timing.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

class Renderer:
    def __init__(self,plan,timing):
        self.plan=plan;self.t=timing;self.duration=timing['duration'];self.cards=[]
        # A subtle radial background, rendered once.
        yy,xx=np.mgrid[0:H,0:W];glow=np.exp(-((xx-850)**2+(yy-650)**2)/(650**2))
        arr=np.zeros((H,W,3),dtype=np.uint8)
        for i,col in enumerate(BG):arr[:,:,i]=col+glow*(8 if i==0 else 19)
        self.base=Image.fromarray(arr,'RGB')
        for index,s in enumerate(timing['scenes']):self.cards.append(self.card(s,index))
        self.captions=[]
        words=timing['words']
        for i in range(0,len(words),5):
            group=words[i:i+5];p=Image.new('RGBA',(960,230),(0,0,0,0));d=ImageDraw.Draw(p)
            d.rounded_rectangle((0,0,959,229),radius=32,fill=(9,20,39,245),outline=(38,74,102,255),width=2)
            para(p,' '.join(w['text'] for w in group),480,80,48,880,maxlines=2)
            self.captions.append((group[0]['start'],group[-1]['end'],p))
    def card(self,s,index):
        im=Image.new('RGBA',(960,1090),(0,0,0,0));d=ImageDraw.Draw(im)
        d.rounded_rectangle((0,0,959,1089),radius=42,fill=(15,29,49,250),outline=(39,72,101,255),width=2)
        d.rounded_rectangle((32,35,135,99),radius=18,fill=(*CYAN,255));txt(im,f'{index+1:02}',(83,69),32,BG)
        txt(im,'الفكرة في لقطة',(910,70),27,MUTED,anchor='rm')
        para(im,s['title'],480,165,57,850,maxlines=2)
        labels=s['labels'];n=len(labels)
        if s['kind']=='comparison':
            for i,label in enumerate(labels):
                x=40+i*int(880/n);ww=int(850/n)
                d.rounded_rectangle((x,410,x+ww,790),radius=26,fill=(19,39,59,255),outline=(*CYAN,255),width=2)
                txt(im,f'{i+1:02}',(x+ww/2,475),40,GOLD)
                para(im,label,x+ww/2,600,38,ww-25,maxlines=3)
        else:
            for i,label in enumerate(labels):
                y=490+i*160
                d.rounded_rectangle((75,y,885,y+130),radius=24,fill=(19,39,59,255),outline=(46,89,117,255),width=2)
                d.rounded_rectangle((835,y+23,847,y+105),radius=6,fill=(*CYAN,255))
                para(im,label,450,y+49,42,720,maxlines=2)
        txt(im,'ما الجديد؟  •  ماذا يعني لك؟',(480,1025),26,MUTED)
        return im
    def frame(self,t):
        im=self.base.copy();d=ImageDraw.Draw(im)
        # Slow grid drift and a progress indicator supply continuous motion.
        shift=int(t*8)%90
        for x in range(-90,W+90,90):d.line((x+shift,200,x+shift,1600),fill=(14,32,49),width=1)
        d.rounded_rectangle((60,92,1020,210),radius=28,fill=(11,27,45),outline=(33,78,101),width=2)
        txt(im,'كل يوم',(950,147),46,anchor='rm');txt(im,'AI',(700,147),46,CYAN);txt(im,'تحديث موثّق',(110,149),26,CYAN,anchor='lm')
        txt(im,self.plan['source']['publisher'],(540,263),30,MUTED)
        index=next((i for i,s in enumerate(self.t['scenes']) if s['start']<=t<s['end']),len(self.cards)-1)
        s=self.t['scenes'][index];local=t-s['start'];reveal=min(1,max(0,local/.55));ease=1-(1-reveal)**3
        card=self.cards[index];im.paste(card,(60,340+int((1-ease)*90)),card)
        # Abstract chip/network icon, clearly illustrative rather than benchmark data.
        cx,cy=540,740
        if s['kind']!='comparison':
            pulse=1+math.sin(t*2.4)*.05;rr=61*pulse
            d=ImageDraw.Draw(im);d.rounded_rectangle((cx-rr,cy-rr,cx+rr,cy+rr),radius=20,outline=CYAN,width=3)
            txt(im,'AI',(cx,cy),40,CYAN)
            for k in range(6):
                ang=k*math.tau/6+t*.09;x=cx+math.cos(ang)*135;y=cy+math.sin(ang)*110
                d.line((cx,cy,x,y),fill=(35,100,128),width=2);d.ellipse((x-7,y-7,x+7,y+7),fill=CYAN)
        for start,end,p in self.captions:
            if start<=t<end:im.paste(p,(60,1480),p);break
        txt(im,'المصدر: '+self.plan['source']['url'].split('/')[2],(540,1770),25,MUTED)
        txt(im,self.plan['source']['published'][:10],(540,1822),25,MUTED)
        d=ImageDraw.Draw(im);d.rounded_rectangle((60,1861,1020,1869),radius=4,fill=(29,47,66));d.rounded_rectangle((60,1861,60+int(960*min(1,t/self.duration)),1869),radius=4,fill=CYAN)
        return im
    def encode(self,path):
        frames=math.ceil(self.duration*FPS)
        p=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],stdin=subprocess.PIPE)
        try:
            for i in range(frames):
                p.stdin.write(self.frame(i/FPS).tobytes())
                if i%(FPS*10)==0:print(f'Rendering {i/FPS:.0f}/{self.duration:.0f} seconds',flush=True)
            p.stdin.close()
            if p.wait()!=0:raise RuntimeError('FFmpeg visual render failed')
        except BaseException:
            p.kill();raise
