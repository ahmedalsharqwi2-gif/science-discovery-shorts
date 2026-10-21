"""Native 1080p motion diagrams for the spoken propeller explanation."""
from functools import lru_cache
import math
from PIL import Image, ImageDraw
from scripts.motion_graphics import label

BG = '#081723'
CYAN = '#59e0e6'
GOLD = '#f3c778'
WHITE = '#eff6f5'
MUTED = '#92aebb'
TITLES = {'rotor':'جناح بيلف', 'airfoil':'مقطع الشفرة', 'speed':'نفس اللفة، مسار أطول',
          'twist':'زاوية الشفرة بتتغير', 'energy':'الطاقة بتنتقل للهوا',
          'airflow':'الهوا بيتحرك والدفع بيتولد', 'pressure':'فرق الضغط حوالين المروحة',
          'losses':'الكفاءة مش كاملة'}


def ease(x):
    x = max(0., min(1., x))
    return x*x*(3-2*x)


def arrow(d, a, b, color=CYAN, width=6, progress=1.):
    x,y=a; bx=x+(b[0]-x)*progress; by=y+(b[1]-y)*progress
    if math.hypot(bx-x,by-y)<3:return
    d.line((a,(bx,by)),fill=color,width=width)
    angle=math.atan2(by-y,bx-x)
    d.polygon([(bx,by),(bx-19*math.cos(angle-.55),by-19*math.sin(angle-.55)),
               (bx-19*math.cos(angle+.55),by-19*math.sin(angle+.55))],fill=color)


def rotor(d, cx, cy, radius, t, color=CYAN):
    for blade in range(3):
        a=blade*math.tau/3+t*.65
        def point(r,s):return cx+r*math.cos(a)+s*math.cos(a+math.pi/2),cy+r*math.sin(a)+s*math.sin(a+math.pi/2)
        d.polygon([point(radius*.12,-20),point(radius*.9,-35),point(radius,0),
                   point(radius*.85,38),point(radius*.2,30)],fill='#397e91',outline=color,width=3)
        d.line([point(radius*.24,0),point(radius*.88,0)],fill='#b9e3df',width=2)
    d.ellipse((cx-35,cy-35,cx+35,cy+35),fill=GOLD,outline=WHITE,width=3)


def section(d,cx,cy,width,angle,color=CYAN):
    points=[]
    for side,indices in [(1,range(61)),(-1,range(60,-1,-1))]:
        for i in indices:
            x=i/60; y=side*5*.14*(.2969*math.sqrt(x)-.126*x-.3516*x*x+.2843*x**3-.1015*x**4)
            px=(x-.5)*width;py=y*width
            points.append((cx+px*math.cos(angle)-py*math.sin(angle),cy+px*math.sin(angle)+py*math.cos(angle)))
    d.polygon(points,fill='#306c80',outline=color,width=3)
    d.line((cx-width*.48*math.cos(angle),cy-width*.48*math.sin(angle),
            cx+width*.48*math.cos(angle),cy+width*.48*math.sin(angle)),fill=GOLD,width=3)


@lru_cache(1)
def background():
    im=Image.new('RGB',(1080,1920),BG);d=ImageDraw.Draw(im)
    for y in range(1920):
        shade=int(9*max(0,1-abs(y-900)/950))
        d.line((0,y,1080,y),fill=(8+shade,23+shade,35+shade))
    d.rounded_rectangle((60,75,1020,176),radius=28,fill='#132d3b')
    label(im,'أسرار الكون',540,126,38,CYAN)
    d.rounded_rectangle((65,535,1015,1450),radius=42,fill='#102b3a',outline='#2d4b5b',width=2)
    label(im,'رسم مبسط للشرح، الحركة مش مقياس للسرعة الحقيقية',540,1585,26,MUTED,width=900,maxlines=2)
    return im


def semantic_frame(scene,t,duration):
    active=[b for b in scene['motion_beats'] if b['at']<=t+.0001]
    beat=active[-1]; kind=beat['concept']; p=ease((t-beat['at'])/.45)
    absolute=scene['start']+t
    im=background().copy();d=ImageDraw.Draw(im)
    label(im,TITLES[kind],540,337,59,WHITE,width=900,maxlines=2)
    if kind in ('rotor','airfoil'):
        if kind=='rotor':
            d.ellipse((245,680,835,1270),outline='#325567',width=2)
            rotor(d,540,975,265,absolute)
            label(im,'شفرة بتلف حوالين المحور',540,1350,36,CYAN)
        else:
            for row in range(5):
                y=820+row*75
                for k in range(5):
                    x=130+(k*180+absolute*70)%780
                    arrow(d,(x,y),(x+65,y),'#33566b',3)
            section(d,540,990,660,-.16)
            label(im,'مقطع يشبه جناح الطائرة',540,1270,37,CYAN)
    elif kind=='speed':
        cx,cy=540,970;a=absolute*.62
        for radius,color in [(120,GOLD),(275,CYAN)]:
            d.ellipse((cx-radius,cy-radius,cx+radius,cy+radius),outline=color,width=4)
            x,y=cx+radius*math.cos(a),cy+radius*math.sin(a)
            d.line((cx,cy,x,y),fill=color,width=3)
            d.ellipse((x-12,y-12,x+12,y+12),fill=color)
            arrow(d,(x,y),(x-radius*.35*math.sin(a),y+radius*.35*math.cos(a)),color,5,p)
        d.ellipse((528,958,552,982),fill=WHITE)
        label(im,'قرب المحور',320,1320,32,GOLD)
        label(im,'عند الطرف',790,1320,32,CYAN)
        label(im,'المسار الأوسع، حركة أسرع',540,625,34,WHITE)
    elif kind=='twist':
        for idx,(y,angle) in enumerate([(775,-.44),(1010,-.23),(1245,-.08)]):
            d.line((230,y,830,y),fill='#33586a',width=2)
            section(d,540,y,510,angle*p)
        label(im,'ناحية المحور',540,610,31,GOLD)
        label(im,'ناحية الطرف',540,1385,31,CYAN)
    elif kind in ('pressure','airflow'):
        # Front is left and wake is right in this side-view schematic.
        if kind=='pressure':
            d.rounded_rectangle((110,740,480,1235),radius=28,fill='#163e5a')
            d.rounded_rectangle((600,740,970,1235),radius=28,fill='#54453a')
            label(im,'قدام المروحة',300,655,30,CYAN)
            label(im,'ورا المروحة',790,655,30,GOLD)
            label(im,'ضغط أقل',300,1305,34,CYAN)
            label(im,'ضغط أعلى',790,1305,34,GOLD)
        for row in range(6):
            y=790+row*65
            for col in range(7):
                x=110+(col*125+absolute*(60 if col<3 else 85))%820
                arrow(d,(x,y),(x+45,y),CYAN if x<540 else GOLD,3,p)
        d.rounded_rectangle((523,745,557,1215),radius=15,fill=WHITE)
        d.ellipse((505,955,575,1025),fill=GOLD)
        if kind=='airflow':
            arrow(d,(500,1340),(245,1340),GOLD,8,p)
            label(im,'الدفع',360,1390,31,GOLD)
            label(im,'اتجاه حركة الهوا',730,655,33,CYAN)
    elif kind=='energy':
        for idx,title in enumerate(['المحرك','المروحة','الهوا']):
            x=235+idx*305
            d.rounded_rectangle((x-115,825,x+115,1120),radius=30,fill='#1a4051',outline=CYAN,width=3)
            label(im,title,x,1195,34,WHITE)
            if idx==0:
                d.rounded_rectangle((x-65,900,x+65,1040),radius=16,fill='#4b7280')
                d.line((x+65,960,x+100,960),fill=GOLD,width=8)
            elif idx==1:rotor(d,x,975,93,absolute)
            else:
                for row in range(3):arrow(d,(x-70,920+row*45),(x+65,920+row*45),CYAN,4)
            if idx<2:
                q=ease((t-beat['at']-.15*idx)/.5)
                arrow(d,(x+125,970),(x+180,970),GOLD,6,q)
        label(im,'طاقة للحركة، ثم للهوا',540,1330,37,GOLD)
    else:
        rotor(d,540,965,220,absolute)
        for index in range(6):
            a=index*math.tau/6+absolute*.6
            cx=540+260*math.cos(a);cy=965+260*math.sin(a)
            d.arc((cx-35,cy-35,cx+35,cy+35),20+absolute*70,280+absolute*70,fill=GOLD,width=4)
        label(im,'خسائر عند أطراف الشفرات',540,1330,34,GOLD)
    d.line((80,1845,1000,1845),fill='#2d4a5c',width=4)
    d.line((80,1845,80+920*min(1,t/max(duration,.01)),1845),fill=CYAN,width=5)
    label(im,'موشن جرافيك مرتبط بالتعليق',540,1895,25,MUTED)
    return im
