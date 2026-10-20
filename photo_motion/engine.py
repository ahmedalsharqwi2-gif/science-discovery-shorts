"""Deterministic 1080x1920 photo motion, preserving the approved Arabic typography."""
from pathlib import Path
from functools import lru_cache
import argparse, hashlib, io, json, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from .contract import ROOT, validate, media_info, digest
W,H,FPS=1080,1920,30

def ease(v):
    v=max(0,min(1,v));return v*v*(3-2*v)
def lerp(a,b,t):return a+(b-a)*t
@lru_cache(None)
def font(n,bold=False):
    return ImageFont.truetype(str(ROOT/'assets'/('NotoSansArabic-Bold.ttf' if bold else 'NotoSansArabic-Regular.ttf')),n)
@lru_cache(500)
def label(s,size,col,bold=False):
    f=font(size,bold);b=f.getbbox(s,direction='rtl')
    im=Image.new('RGBA',(b[2]-b[0]+12,b[3]-b[1]+14));d=ImageDraw.Draw(im)
    d.text((6-b[0],7-b[1]),s,font=f,fill=col,direction='rtl');return im

def text(im,s,x,y,size,col,bold=False,alpha=1):
    st=label(s,size,col,bold)
    if alpha<1:
        st=st.copy();st.putalpha(st.getchannel('A').point(lambda a:round(a*max(0,alpha))))
    im.alpha_composite(st,(round(x-st.width/2),round(y)))

def lines(value,size,col,max_width=915):
    rows=[];row=''
    for word in value.split():
        candidate=(row+' '+word).strip()
        if label(candidate,size,col,True).width>max_width:
            if not row:raise ValueError('Caption contains an unbreakable word outside safe area')
            rows.append(row);row=word
        else:row=candidate
    if row:rows.append(row)
    if any(label(row,size,col,True).width>max_width for row in rows):raise ValueError('Caption exceeds safe width')
    if len(rows)>3:raise ValueError('Caption needs more than three safe rows; split using actual speech timings')
    return rows

class Renderer:
    def __init__(self,manifest):
        self.data,self.profile,self.paths,self.audio_meta=validate(manifest)
        self.duration=self.data['duration'];self.scenes=self.data['scenes']
        self.images={key:Image.open(path).convert('RGBA') for key,path in self.paths.items() if key!=self.data['audio']['path']}
        self.caption_rows=[lines(c['text'],self.profile['caption_size'],self.profile['cream']) for c in self.data['captions']]
        for scene in self.scenes:
            if label(scene.get('title',''),self.profile['title_size'],self.profile['cream'],True).width>920:
                raise ValueError('Scene title exceeds safe width; shorten it')
            for layer in scene.get('layers',[]):
                im=self.images[layer['path']];box=im.getchannel('A').getbbox()
                if box:self.images[layer['path']]=im.crop(box)
        self.shade=Image.new('RGBA',(W,H));a=np.zeros((H,W),np.uint8)
        a[:600,:]=np.linspace(165,0,600,dtype=np.uint8)[:,None]
        a[1430:,:]=np.linspace(0,230,H-1430,dtype=np.uint8)[:,None]
        self.shade.putalpha(Image.fromarray(a))
    def shot(self,scene,t):
        u=ease((t-scene['start'])/(scene['end']-scene['start']))
        start=scene.get('camera_start',[1.04,0,0]);end=scene.get('camera_end',[1.10,0,0])
        zoom,x,y=[lerp(a,b,u) for a,b in zip(start,end)]
        source=self.images[scene['background']];sw,sh=source.size
        scale=max(W/sw,H/sh)*zoom;nw,nh=round(sw*scale),round(sh*scale)
        im=source.transform((W,H),Image.Transform.AFFINE,(1/scale,0,(nw-W)/2/scale+x/scale,0,1/scale,(nh-H)/2/scale+y/scale),Image.Resampling.BICUBIC)
        for layer in scene.get('layers',[]):
            values=[lerp(a,b,u) for a,b in zip(layer['start'],layer['end'])]
            x,y,height=values;source=self.images[layer['path']]
            image=source.resize((round(source.width*height/source.height),round(height)),Image.Resampling.LANCZOS)
            opacity=layer.get('opacity',1)
            if opacity!=1:image.putalpha(image.getchannel('A').point(lambda a:round(a*opacity)))
            im.alpha_composite(image,(round(x),round(y)))
        if scene.get('overlay'):im.alpha_composite(self.images[scene['overlay']])
        d=ImageDraw.Draw(im);accent=self.profile['accent']
        for route in scene.get('routes',[]):
            points=route['points'];progress=ease((t-scene['start'])/2)
            lengths=[math.dist(a,b) for a,b in zip(points,points[1:])];remaining=sum(lengths)*progress
            for a,b,length in zip(points,points[1:],lengths):
                if remaining<=0:break
                k=min(1,remaining/length) if length else 1
                d.line([tuple(a),(lerp(a[0],b[0],k),lerp(a[1],b[1],k))],fill=accent,width=4);remaining-=length
        for locator in scene.get('locators',[]):
            x,y=locator['position'];r=19+6*math.sin((t-scene['start'])*2)
            d.ellipse((x-r,y-r,x+r,y+r),outline=accent,width=3)
            d.ellipse((x-6,y-6,x+6,y+6),fill=accent)
            tx,ty=locator.get('label_position',[x,y+40])
            text(im,locator['label'],tx,ty,36,accent,True)
        return im
    def frame(self,t):
        index=next((i for i,s in enumerate(self.scenes) if s['start']<=t<s['end']),len(self.scenes)-1)
        scene=self.scenes[index];im=self.shot(scene,t)
        transition=self.profile['transition_seconds']
        if index and t-scene['start']<transition:
            old=self.shot(self.scenes[index-1],scene['start'])
            im=Image.blend(old,im,ease((t-scene['start'])/transition))
        im.alpha_composite(self.shade);p=self.profile
        text(im,p['brand'],540,95,27,p['accent'])
        if scene.get('title'):
            alpha=ease((t-scene['start'])/.45)
            text(im,scene['title'],540,scene.get('title_y',300),p['title_size'],p['cream'],True,alpha)
        if scene.get('subtitle'):text(im,scene['subtitle'],540,425,38,p['accent'],alpha=ease((t-scene['start'])/.5))
        for index,c in enumerate(self.data['captions']):
            if c['start']<=t<c['end']:
                for i,row in enumerate(self.caption_rows[index]):
                    st=label(row,p['caption_size'],p['cream'],True);x=(W-st.width)//2;y=1540+i*77
                    d=ImageDraw.Draw(im);d.rounded_rectangle((x-17,y-10,x+st.width+17,y+st.height+10),radius=10,fill=(5,10,15,180))
                    im.alpha_composite(st,(x,y))
                break
        d=ImageDraw.Draw(im);d.line((90,1815,990,1815),fill=(240,232,216,90),width=2)
        d.line((90,1815,90+900*t/self.duration,1815),fill=p['accent'],width=4)
        text(im,self.data.get('disclosure',p['footer']),540,1860,22,'#d0c5ad')
        return im.convert('RGB')

def render(manifest,output):
    renderer=Renderer(manifest);out=Path(output);out.parent.mkdir(parents=True,exist_ok=True)
    preview=out.parent/'photo-motion-frames';preview.mkdir(exist_ok=True)
    for index,scene in enumerate(renderer.scenes):
        t=(scene['start']+scene['end'])/2
        renderer.frame(t).save(preview/f'scene-{index+1:02d}.jpg',quality=93)
    silent=out.with_suffix('.picture.mp4');frames=round(renderer.duration*FPS)
    command=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(silent)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for n in range(frames):
            process.stdin.write(renderer.frame(n/FPS).tobytes())
            if n%90==0:print(f'Rendering {n}/{frames} frames',flush=True)
        process.stdin.close()
        if process.wait():raise RuntimeError('Video encoder failed')
    except BaseException:
        process.kill();process.wait();raise
    audio=renderer.paths[renderer.data['audio']['path']]
    # No shortest, speed, pitch, normalization, TTS, or narration trimming filters.
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-movflags','+faststart',str(out)],check=True)
    silent.unlink()
    report=verify(renderer,out)
    report['manifest_sha256']=digest(manifest)
    out.with_suffix('.verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
    return out

def verify(renderer,out):
    metadata=media_info(out);v=next(s for s in metadata['streams'] if s['codec_type']=='video');a=next(s for s in metadata['streams'] if s['codec_type']=='audio')
    if (v['width'],v['height'],v['r_frame_rate'])!=(W,H,'30/1') or v['codec_name']!='h264' or a['codec_name']!='aac':
        raise ValueError('Unexpected output format')
    if abs(float(v['duration'])-renderer.duration)>.04 or abs(float(a['duration'])-renderer.duration)>.06:
        raise ValueError('Output does not contain the full approved narration')
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    def pcm(path):
        return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ar','16000','-ac','1','-f','f32le','-']),np.float32)
    source=pcm(renderer.paths[renderer.data['audio']['path']]);actual=pcm(out)
    if abs(len(actual)-len(source))>1024:raise ValueError('Narration length changed')
    n=min(len(source),len(actual));correlation=float(np.corrcoef(source[:n],actual[:n])[0,1])
    if not np.isfinite(correlation) or correlation<.98:raise ValueError('Output narration differs from approved audio')
    comparisons=[]
    # Compare encoded scene midpoints to the exact authored renderer frames.
    for scene in renderer.scenes:
        t=math.floor(((scene['start']+scene['end'])/2)*FPS)/FPS
        data=subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(out),'-frames:v','1','-f','image2pipe','-vcodec','png','-'])
        decoded=np.asarray(Image.open(io.BytesIO(data)).convert('RGB').resize((108,192)),dtype=float)
        expected=np.asarray(renderer.frame(t).resize((108,192)),dtype=float)
        delta=float(np.abs(decoded-expected).mean())
        if delta>6:raise ValueError(f'Encoded scene differs from authored frame: {delta}')
        comparisons.append({'time':t,'mean_pixel_error':round(delta,3)})
    return {'verified':True,'width':W,'height':H,'fps':FPS,'duration':renderer.duration,'voice_pcm_correlation':round(correlation,6),'all_reviewed_asset_hashes_match':True,'full_narration_preserved':True,'encoded_scene_comparisons':comparisons,'new_voice_generated':False,'new_images_generated_in_run':False,'social_publishing':False,'artistic_quality_automatically_certified':False}

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--output',default='output/final_video_full.mp4');p.add_argument('--validate-only',action='store_true');args=p.parse_args()
    if args.validate_only:
        Renderer(args.manifest);print('Approved media, full timeline, Arabic layout and reviews validated.');return
    render(args.manifest,args.output)
if __name__=='__main__':main()
