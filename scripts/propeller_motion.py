"""Native 1080p motion diagrams for the spoken propeller explanation."""
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


def semantic_frame(scene,t,duration):
    from scripts.kinetic_science import mechanism_frame
    return mechanism_frame(scene,t,duration)
