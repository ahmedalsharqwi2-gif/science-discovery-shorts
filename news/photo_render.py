"""Photographic scenes with timed motion, labels and measured speech captions."""
import math
from PIL import Image,ImageDraw,ImageOps,ImageFilter
from news.render import Renderer,W,H,txt,para,CYAN,GOLD,INK,MUTED,BG

class PhotoRenderer(Renderer):
    def __init__(self,plan,timing,images):
        super().__init__(plan,timing)
        if len(images)!=len(timing['scenes']):raise ValueError('Every scene needs its generated image')
        self.photos=[]
        for path in images:
            with Image.open(path) as im:self.photos.append(ImageOps.fit(im.convert('RGB'),(1188,2112),centering=(.5,.48)))
        shade=Image.new('RGBA',(W,H));pixels=[]
        for y in range(H):
            top=max(0,1-y/450)*.82;bottom=max(0,(y-1080)/840)*.96
            pixels.extend([(3,9,20,int(255*max(top,bottom)))]*W)
        shade.putdata(pixels);self.shade=shade
        self.caps=[]
        for start,end,panel in self.captions:self.caps.append((start,end,panel))
    def frame(self,t):
        index=next((i for i,s in enumerate(self.t['scenes']) if s['start']<=t<s['end']),len(self.photos)-1)
        s=self.t['scenes'][index];progress=max(0,min(1,(t-s['start'])/(s['end']-s['start'])))
        smooth=progress*progress*(3-2*progress)
        # Optical camera movement over the scene; no claim of real subject motion.
        zoom=1.015+.055*(smooth if index%2==0 else 1-smooth)
        cw,ch=W/zoom,H/zoom;cx=594+32*math.sin(index+smooth*1.5);cy=1056+26*math.cos(index+smooth)
        im=self.photos[index].crop((round(cx-cw/2),round(cy-ch/2),round(cx+cw/2),round(cy+ch/2))).resize((W,H),Image.Resampling.BICUBIC).convert('RGBA')
        im.alpha_composite(self.shade)
        d=ImageDraw.Draw(im);d.rounded_rectangle((58,86,1022,214),radius=28,fill=(4,15,29,220),outline=(65,223,233,110),width=2)
        txt(im,'على السريع',(445,149),50);txt(im,'ai',(770,149),50,CYAN)
        txt(im,self.plan['source']['publisher'],(540,265),30,MUTED)
        para(im,s['title'],540,350,53,930,maxlines=2)
        # A short source-linked information callout appears on its spoken cue.
        visible=0
        for k,label in enumerate(s['labels']):
            cue=s['label_beats'][k]
            if t<cue:continue
            age=t-cue;settle=1-min(1,age/.35);y=1090+visible*108+round(20*settle);visible+=1
            layer=Image.new('RGBA',(960,96));ld=ImageDraw.Draw(layer)
            ld.rounded_rectangle((0,0,959,95),radius=20,fill=(5,20,33,215),outline=(65,223,233,150),width=2)
            ld.rounded_rectangle((921,17,931,79),radius=4,fill=CYAN)
            para(layer,label,475,25,32,860,maxlines=2);im.alpha_composite(layer,(60,y))
            pulse=math.exp(-max(0,age)*2.7);r=20+50*min(1,age)
            d=ImageDraw.Draw(im);px=180+k*350;py=860+int(25*math.sin(k))
            d.ellipse((px-r,py-r,px+r,py+r),outline=(*CYAN,int(190*pulse)),width=3)
            d.line((px,py+r,px,y),fill=(*CYAN,int(110*pulse)),width=2)
        age=t-s.get('beat',s['end'])
        if 0<=age<2.4:
            bubble=Image.new('RGBA',(960,145));bd=ImageDraw.Draw(bubble)
            bd.rounded_rectangle((0,0,959,144),radius=24,fill=(*GOLD,245))
            para(bubble,s['punchline'],480,43,37,890,fill=BG,maxlines=2)
            im.alpha_composite(bubble,(60,1328))
        for start,end,panel in self.caps:
            if start<=t<end:im.alpha_composite(panel,(60,1500));break
        txt(im,'تصور بصري مولّد • الخبر من المصدر',(540,1750),25,MUTED)
        txt(im,self.plan['source']['url'].split('/')[2],(540,1800),25,MUTED)
        txt(im,self.plan['source']['published'][:10],(540,1840),23,MUTED)
        d=ImageDraw.Draw(im);d.rounded_rectangle((60,1872,1020,1880),radius=4,fill=(29,47,66));d.rounded_rectangle((60,1872,60+int(960*min(1,t/self.duration)),1880),radius=4,fill=CYAN)
        return im.convert('RGB')
