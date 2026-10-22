"""Deterministic motion design overlays, synchronized with real speech cues.

Pure Pillow layer, no provider cost; composites on current photographic shots.
The diagrams are explicitly illustrative, never evidence of real measurements.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw

ACCENTS={"science":(72,216,239),"history":(245,177,92),"horror":(193,143,121),"news":(55,221,198)}
def over(im, seconds, scene, profile):
    if profile not in ACCENTS:return im
    accent=ACCENTS[profile];start=float(scene.get("start",0))
    end=float(scene.get("end",start+1))
    age=max(0,seconds-start)
    if seconds>=end:return im
    w,h=im.size
    layer=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(layer)
    # Stylized, cinematic HUD with correctly cropped frame edges.
    fade=min(1,age/.6,max(0,(end-seconds)/.4))
    a=int(120*fade)
    if profile=="science":
        # Animated microscope/circuit-like nodes; no numerical claims.
        center=(w*.5,h*.51);phase=seconds*.55
        pts=[]
        for k in range(9):
            theta=k*math.tau/9+phase*.08
            x=center[0]+(190+20*math.sin(phase+k))*math.cos(theta)
            y=center[1]+(235+18*math.cos(phase+k))*math.sin(theta)
            pts.append((x,y))
        for i,p in enumerate(pts):
            for j in (2,4):
                q=pts[(i+j)%len(pts)]
                d.line((p[0],p[1],q[0],q[1]),fill=(*accent,max(0,int(a*.27))),width=2)
            r=9+3*math.sin(seconds*2+i)
            d.ellipse((p[0]-r,p[1]-r,p[0]+r,p[1]+r),fill=(*accent,a))
        for k in range(3):
            r=125+k*60+10*math.sin(seconds*.7+k)
            d.arc((center[0]-r,center[1]-r,center[0]+r,center[1]+r),40,325,fill=(*accent,int(a*.48)),width=3)
    elif profile=="history":
        # Map-grid and timeline tracking lines with vintage optical feel.
        for k in range(6):
            y=h*.36+k*65
            d.line((w*.18,y,w*.82,y),fill=(*accent,int(a*.18)),width=2)
        x=w*.22+((seconds-start)*60)%(w*.52)
        d.line((x,h*.38,x,h*.67),fill=(*accent,int(a*.65)),width=3)
        d.ellipse((x-8,h*.59-8,x+8,h*.59+8),fill=(*accent,a))
        d.arc((w*.25,h*.36,w*.75,h*.65),200,330,fill=(*accent,int(a*.5)),width=4)
    elif profile=="horror":
        # Slow horizontal shadows and atmospheric pulse; no strobe.
        for k in range(4):
            y=h*.36+k*110+15*math.sin(seconds*.4+k)
            d.line((w*.13,y,w*.87,y),fill=(*accent,int(a*.12)),width=3)
        r=90+35*math.sin(seconds*.55)
        d.arc((w*.5-r,h*.56-r,w*.5+r,h*.56+r),30,270,fill=(*accent,int(a*.38)),width=3)
    else:
        # News data flow nodes and header underline, deliberately no invented stats.
        for k in range(7):
            x=w*.2+k*w*.1;y=h*.56+48*math.sin(seconds*.65+k*.75)
            d.ellipse((x-7,y-7,x+7,y+7),fill=(*accent,a))
            if k:
                prev=w*.2+(k-1)*w*.1;yp=h*.56+48*math.sin(seconds*.65+(k-1)*.75)
                d.line((prev,yp,x,y),fill=(*accent,int(a*.5)),width=3)
        width=(.2+.8*min(1,age/1.5))*w*.66
        d.rounded_rectangle((w*.17,h*.25,w*.17+width,h*.25+5),radius=2,fill=(*accent,int(a*.7)))
    im.alpha_composite(layer)
    return im
