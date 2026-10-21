"""Original editorial motion graphics. Schematics are illustrations, never archival footage."""
from pathlib import Path
from functools import lru_cache
import math,re,subprocess
from PIL import Image,ImageDraw,ImageFont
W,H=1080,1920
@lru_cache(None)
def font(size):
    choices=[Path(__file__).resolve().parents[1]/'photo_motion/assets/NotoSansArabic-Bold.ttf',Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf'),Path('/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf')]
    choices+=list(Path('/usr/share/fonts').rglob('NotoSansArabic-Bold.ttf'))
    p=next((p for p in choices if p.exists()),None)
    if p is None:raise RuntimeError('Arabic font missing; cannot render professional motion')
    return ImageFont.truetype(str(p),size)
def clean(text):return re.sub(r'[\u0610-\u061a\u064b-\u065f\u0670ـ]','',str(text))
def label(im,text,x,y,size=44,color='#eee9dd',width=860,maxlines=3):
    d=ImageDraw.Draw(im);words=clean(text).split();rows=[];row=''
    for word in words:
        candidate=(row+' '+word).strip()
        if d.textlength(candidate,font=font(size),direction='rtl')>width and row:rows.append(row);row=word
        else:row=candidate
    if row:rows.append(row)
    if len(rows)>maxlines:
        return label(im,text,x,y,max(28,size-6),color,width,maxlines+1)
    for i,row in enumerate(rows):d.text((x,y+i*size*1.65),row,font=font(size),fill=color,anchor='mm',direction='rtl')
def frame(scene,profile,t,duration):
    bg={'history':'#101b20','science':'#071726','horror':'#0b101c'}[profile]
    accent={'history':'#edb76e','science':'#57e2ec','horror':'#d09180'}[profile]
    im=Image.new('RGB',(W,H),bg);d=ImageDraw.Draw(im)
    shift=int(t*9)%80
    for x in range(-80,W+80,80):d.line((x+shift,250,x+shift,1550),fill='#172b35')
    for y in range(300,1560,80):d.line((45,y,1035,y),fill='#172b35')
    d.rounded_rectangle((45,75,1035,190),radius=25,fill='#132530',outline=accent,width=2)
    brand={'history':'على خط الحكاية','science':'أسرار الكون','horror':'قبل ما تطفي النور'}[profile]
    label(im,brand,540,130,40,accent)
    title=' '.join(clean(scene['text']).split()[:9])
    label(im,title,540,370,54,width=900,maxlines=2)
    context=clean(scene.get('prompt','')+' '+scene.get('query','')+' '+scene['text'])
    if profile=='history' and re.search('سور|أسوار|حصار|قلع|مدافع|حجارة|القسطنط|المدينة',clean(scene['text'])):
        # A schematic fortified city: no invented troop coordinates or geography.
        d.rounded_rectangle((90,650,990,1320),radius=30,fill='#162c32',outline='#43636a',width=2)
        for i in range(11):
            x=135+i*75;top=890+int(9*math.sin(t+i))
            d.rectangle((x,top,x+72,1170),fill='#5e655c',outline='#a4a58c',width=3)
            for row in range(5):d.line((x,top+row*55,x+72,top+row*55),fill='#88907c',width=2)
        for x in [145,795]:
            d.rectangle((x,760,x+130,1170),fill='#787e6e',outline=accent,width=3)
            for k in range(3):d.rectangle((x+k*45,725,x+k*45+25,775),fill='#8d917e',outline=accent,width=2)
            d.rounded_rectangle((x+44,830,x+87,965),radius=15,fill=bg,outline=accent,width=2)
        d.pieslice((430,910,650,1260),180,360,fill=bg,outline=accent,width=3)
        d.rectangle((430,1080,650,1175),fill=bg)
        # Animated emphasis brackets show a change in focus, not a claimed event position.
        cx=540+280*math.sin(t*.55);cy=975;rr=95+12*math.sin(t*2)
        d.arc((cx-rr,cy-rr,cx+rr,cy+rr),20,140,fill=accent,width=5)
        d.arc((cx-rr,cy-rr,cx+rr,cy+rr),200,320,fill=accent,width=5)
        label(im,'رسم توضيحي • عمارة وحصار',540,1250,30,accent)
    elif profile=='history':
        d.rounded_rectangle((90,650,990,1390),radius=30,fill='#162c32',outline='#43636a',width=2)
        d.ellipse((310,730,770,1190),outline=accent,width=9)
        for k in range(12):
            a=k*math.tau/12;x=540+195*math.sin(a);y=960-195*math.cos(a)
            d.ellipse((x-5,y-5,x+5,y+5),fill=accent)
        a=t*.35;d.line((540,960,540+130*math.sin(a),960-130*math.cos(a)),fill=accent,width=7)
        label(im,'تفاصيل بتغير الحكاية',540,1300,39,accent)
    elif profile=='science' and re.search('مراوح|مروحي|شفرات|شفرة|propeller|rotor',context,re.I):
        d.rounded_rectangle((85,650,995,1420),radius=28,fill='#102e3e',outline='#2d6478',width=3)
        cx,cy=540,950
        for k in range(4):
            a=k*math.tau/4+t*.6
            def pt(radius,side):return (cx+radius*math.cos(a)+side*math.cos(a+math.pi/2),cy+radius*math.sin(a)+side*math.sin(a+math.pi/2))
            d.polygon([pt(60,-42),pt(300,-22),pt(335,5),pt(285,36),pt(90,47)],fill='#5dafbb',outline=accent,width=4)
            d.line([pt(80,0),pt(300,0)],fill='#e6f2c7',width=3)
        d.ellipse((485,895,595,1005),fill='#e4bc70',outline='#fbf0ce',width=4)
        for i in range(9):
            y=735+i*56;x=150+((t*70+i*53)%760)
            d.line((x,y,x+75,y),fill='#3e7e95',width=3)
        label(im,'قرب المحور',300,1290,33,accent);label(im,'عند الطرف',785,1290,33,accent)
        d.line((215,1350,350,1350),fill=accent,width=5);d.polygon([(350,1350),(330,1338),(330,1362)],fill=accent)
        d.line((650,1350,900,1350),fill=accent,width=5);d.polygon([(900,1350),(880,1338),(880,1362)],fill=accent)
        label(im,'مروحة مبسطة • الأسهم توضيحية',540,720,30,accent)
    elif profile=='science':
        center=(540,960)
        for ring in [170,300]:d.ellipse((540-ring,960-ring,540+ring,960+ring),outline='#276078',width=3)
        for k in range(7):
            a=k*math.tau/7+t*.27;x=540+300*math.cos(a);y=960+240*math.sin(a)
            d.line((*center,x,y),fill='#34778a',width=4);d.ellipse((x-29,y-29,x+29,y+29),fill=accent,outline='#e1feff',width=3)
            px=540+(x-540)*((t*.55+k/7)%1);py=960+(y-960)*((t*.55+k/7)%1)
            d.ellipse((px-9,py-9,px+9,py+9),fill='#fff1b5')
        d.rounded_rectangle((427,850,653,1070),radius=38,fill='#194154',outline=accent,width=5)
        label(im,'الفكرة',540,960,51,accent)
        label(im,'علاقات توضيحية • بدون قياسات مفترضة',540,1350,27,accent)
    elif profile=='horror' and re.search('سفينة|سيليست|شراعية|Mary|ship|sailing',context,re.I):
        d.rounded_rectangle((85,650,995,1440),radius=28,fill='#0c2132',outline='#355367',width=3)
        d.ellipse((800,720,890,810),fill='#afc4ca')
        cy=1100+7*math.sin(t*.7)
        for row in range(5):
            points=[(x,1210+row*38+9*math.sin(x*.018-t*1.5-row)) for x in range(95,990,8)]
            d.line(points,fill='#477487',width=3)
        d.polygon([(220,cy),(895,cy),(790,cy+170),(340,cy+170)],fill='#604f40',outline=accent,width=4)
        for y in range(1,5):d.line((265,cy+y*25,850,cy+y*25),fill='#89735b',width=2)
        for x,h in [(455,350),(645,400)]:
            d.line((x,cy,x,cy-h),fill=accent,width=7)
            d.polygon([(x+9,cy-h+30),(x+155,cy-35),(x+9,cy-35)],fill='#b2bec0',outline=accent,width=2)
            d.line((x,cy-h,260,cy),fill='#617885',width=2)
        d.rectangle((350,cy-60,790,cy),fill='#415767',outline=accent,width=3)
        label(im,'تصور توضيحي لسفينة شراعية',540,1380,30,accent)
    else:
        # Original suspense set: door, shadow, drifting light and dust.
        d.polygon([(90,660),(990,660),(850,1380),(230,1380)],fill='#101b27',outline='#344859')
        d.rectangle((330,680,750,1380),fill='#071018',outline='#697581',width=8)
        gap=25+65*(.5+.5*math.sin(t*.6));d.polygon([(350,705),(710-gap,725),(710-gap,1330),(350,1350)],fill='#26343d',outline=accent,width=4)
        d.ellipse((650-gap,1050,674-gap,1074),fill=accent)
        for i in range(25):
            x=130+(i*83)%820;y=700+((i*57+t*17)%650);d.ellipse((x,y,x+3,y+3),fill='#889596')
        d.arc((180,760,900,1340),int(t*18)%360,int(t*18)%360+100,fill=accent,width=3)
        label(im,'مشهد توضيحي للسرد',540,1450,29,accent)
    # Static narrative callout; precise word captions are composited by the main pipeline.
    takeaway=' '.join(clean(scene['text']).split()[-7:])
    d.rounded_rectangle((65,1535,1015,1725),radius=28,fill='#172b35',outline=accent,width=2)
    label(im,takeaway,540,1620,44,accent,width=860,maxlines=2)
    d.line((70,1820,1010,1820),fill='#3d535e',width=3)
    d.line((70,1820,70+940*min(1,t/max(duration,.1)),1820),fill=accent,width=6)
    label(im,'رسوم توضيحية أصلية',540,1870,25,'#a7bcc3')
    return im

def render_explainer(output,seconds,scene,cfg):
    if not str(scene.get('text','')).strip() or seconds<=0:raise ValueError('Empty motion scene')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);fps=cfg['fps']
    if cfg['width']*16!=cfg['height']*9:raise ValueError('Motion graphics requires 9:16')
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(fps),'-i','pipe:0','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t',str(seconds),'-map','0:v','-map','1:a','-vf',f"scale={cfg['width']}:{cfg['height']}",'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac',str(output)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for n in range(math.ceil(seconds*fps)):p.stdin.write(frame(scene,cfg['profile'],n/fps,seconds).tobytes())
        p.stdin.close()
        if p.wait():raise RuntimeError('Motion encoding failed')
    except BaseException:p.kill();raise
