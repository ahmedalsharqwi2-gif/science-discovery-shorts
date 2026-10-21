"""Mechanism animation with moving sections, flow particles and tip vortices."""
import math
from PIL import Image,ImageDraw
from scripts.motion_graphics import label
from scripts.propeller_motion import arrow,rotor,section,CYAN,GOLD,WHITE,MUTED,TITLES

W,H=1080,1920


def flow(d,t,y0=960,pressure=False):
    for row in range(9):
        y=y0-265+row*62
        for col in range(7):
            phase=(col/7+t*.13+row*.047)%1
            x=75+930*phase
            bend=math.sin(phase*math.pi)*(.55-abs(row-4)/8)*36
            yy=y+bend
            color=CYAN if x<540 else GOLD
            arrow(d,(x,yy),(x+35+(12 if x>540 else 0),yy),color,3)


def moving_airfoil(d,t):
    section(d,540,1010,740,-.13)
    for side in (-1,1):
        for row in range(4):
            points=[]
            for x in range(65,1020,15):
                u=(x-540)/400
                bump=math.exp(-u*u*3)*(45+row*9)
                y=1010+side*(64+row*65+bump)-.13*(x-540)
                points.append((x,y))
            d.line(points,fill='#365b70',width=2)
            for particle in range(5):
                x=65+((particle*190+t*105+row*44)%940);u=(x-540)/400
                y=1010+side*(64+row*65+math.exp(-u*u*3)*(45+row*9))-.13*(x-540)
                d.ellipse((x-5,y-5,x+5,y+5),fill=CYAN)


def blade_mesh(d,t,age):
    camera=.34*math.sin(t*.24)
    def point(u,edge):
        twist=-.55+.44*u
        width=140-58*u
        xx=edge*width*math.cos(twist+camera)
        zz=edge*width*math.sin(twist+camera)
        return (540+xx+zz*.38,1370-u*710+zz*.5)
    for i in range(27):
        u=i/27;v=(i+1)/27
        col=(49+i*2,126+i*2,145+i*2)
        d.polygon([point(u,-1),point(v,-1),point(v,1),point(u,1)],fill=col,outline='#7ac4cb')
    cursor=(age*.24)%1
    a,b=point(cursor,-1),point(cursor,1)
    d.line((a,b),fill=GOLD,width=8)
    d.ellipse((a[0]-7,a[1]-7,a[0]+7,a[1]+7),fill=GOLD)
    section(d,855,850+cursor*270,230,-.55+.44*cursor,GOLD)
    d.line((b,(760,850+cursor*270)),fill='#9a987c',width=2)


def mechanism_frame(scene,t,duration):
    absolute=scene['start']+t
    beat=[b for b in scene['motion_beats'] if b['at']<=t+.0001][-1]
    kind=beat['concept'];age=max(0,absolute-beat.get('origin',scene['start']+beat['at']))
    im=Image.new('RGB',(W,H),'#071c2b');d=ImageDraw.Draw(im)
    for y in range(520,1650,80):d.line((20,y,1060,y),fill='#133347',width=1)
    for x in range(20,1080,80):d.line((x,520,x,1650),fill='#133347',width=1)
    d.ellipse((95,570,985,1460),outline='#234b60',width=2)
    if kind in ('rotor','losses'):
        rotor(d,540,1005,345,absolute)
        for blade in range(3):
            a=blade*math.tau/3+absolute*.65
            x,y=540+345*math.cos(a),1005+345*math.sin(a)
            if kind=='losses':
                for k in range(14):
                    q=k/14;angle=a+q*math.tau+absolute*.7
                    xx=x+(25+q*70)*math.cos(angle);yy=y+(25+q*70)*math.sin(angle)
                    d.ellipse((xx-4,yy-4,xx+4,yy+4),fill=GOLD)
        label(im,'دوامات عند الأطراف' if kind=='losses' else 'المروحة بتلف وتحرك الهوا',540,1515,38,GOLD if kind=='losses' else CYAN)
    elif kind=='airfoil':
        moving_airfoil(d,absolute)
        label(im,'المقطع الجانبي للشفرة',540,1515,38,CYAN)
    elif kind=='twist':
        blade_mesh(d,absolute,age)
        label(im,'قرب المحور',340,1390,30,GOLD)
        label(im,'ناحية الطرف',340,650,30,CYAN)
        label(im,'الميل بيتغير على طول الشفرة',540,1515,37,WHITE)
    elif kind=='speed':
        a=absolute*.74
        for r,color in [(145,GOLD),(350,CYAN)]:
            d.ellipse((540-r,1005-r,540+r,1005+r),outline='#3b6073',width=3)
            for k in range(20):
                aa=a-k*.028;x=540+r*math.cos(aa);y=1005+r*math.sin(aa)
                size=3+7*(1-k/20)
                d.ellipse((x-size,y-size,x+size,y+size),fill=color)
            x=540+r*math.cos(a);y=1005+r*math.sin(a)
            d.line((540,1005,x,y),fill=color,width=3)
            arrow(d,(x,y),(x-r*.3*math.sin(a),y+r*.3*math.cos(a)),color,6)
        label(im,'نفس زمن اللفة',540,600,34,WHITE)
        label(im,'مسار أقصر',275,1465,31,GOLD);label(im,'مسار أطول',805,1465,31,CYAN)
    elif kind in ('pressure','airflow'):
        if kind=='pressure':
            d.rounded_rectangle((80,700,480,1330),radius=90,fill='#123c57')
            d.rounded_rectangle((600,700,1000,1330),radius=90,fill='#514437')
        flow(d,absolute,1005,kind=='pressure')
        # Side view of the rotor plane, not an arbitrary moving object.
        width=12+30*abs(math.sin(absolute*2.8))
        d.ellipse((540-width,690,540+width,1320),outline=WHITE,width=5)
        d.ellipse((505,970,575,1040),fill=GOLD)
        if kind=='pressure':
            label(im,'ضغط أقل قدام',285,1450,31,CYAN);label(im,'ضغط أعلى ورا',795,1450,31,GOLD)
        else:
            arrow(d,(500,1450),(205,1450),GOLD,9)
            label(im,'الدفع',350,1510,34,GOLD)
    else:
        # Crank motion turns a shaft; the propeller accelerates visible particles.
        cx,cy=230,1005
        d.rounded_rectangle((90,780,365,1215),radius=25,fill='#284a5c',outline=CYAN,width=3)
        piston=810+45*math.sin(absolute*2)
        d.rectangle((140,piston,300,piston+55),fill='#83aeb4')
        d.line((220,piston+55,240+50*math.cos(absolute*2),1005+50*math.sin(absolute*2)),fill=GOLD,width=12)
        d.ellipse((185,950,295,1060),outline=GOLD,width=5)
        d.line((295,1005,530,1005),fill=GOLD,width=13)
        rotor(d,570,1005,220,absolute*1.5)
        for row in range(6):
            y=815+row*72
            for k in range(3):
                x=795+(k*80+absolute*100)%240
                arrow(d,(x,y),(x+35,y),CYAN,4)
        label(im,'المحرك',225,1400,32,GOLD);label(im,'المروحة',570,1400,32,WHITE);label(im,'الهوا',900,1400,32,CYAN)
    # Fixed text and captions remain independent of camera motion.
    d.rectangle((0,0,W,235),fill='#0a1723')
    label(im,'اسرار الكون',540,126,38,CYAN)
    label(im,TITLES[kind],540,335,57,WHITE,width=920,maxlines=2)
    d.rectangle((0,1650,W,H),fill='#071420')
    label(im,'تحريك توضيحي، وليس قياسًا للسرعة أو الضغط',540,1890,24,MUTED)
    return im
