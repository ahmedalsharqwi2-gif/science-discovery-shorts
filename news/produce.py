import json, math, wave, subprocess, os
from pathlib import Path
import numpy as np
from voice_provider.client import generate
from news.editor import prepare
from news.render import align, Renderer
from news.delivery import mix_audio,verify_tail

def soundtrack(duration,scenes):
    rate=48000;t=np.arange(math.ceil(duration*rate))/rate
    # Original synthesized score and short UI accents; no stock licensing/API dependency.
    bed=np.zeros_like(t)
    for k,f in enumerate((110,164.8138,220,261.6256)):
        envelope=.45+.25*np.sin(2*np.pi*t/(9+k))
        bed+=.035*envelope*np.sin(2*np.pi*f*t + .2*np.sin(t*.7))
    bed*=np.minimum(1,t/1.5)*np.minimum(1,(duration-t)/2).clip(0,1)
    fx=np.zeros_like(t)
    for scene in scenes:
        local=t-scene['start'];mask=(local>=0)&(local<.22)
        z=local[mask];fx[mask]+=.07*np.exp(-22*z)*np.sin(2*np.pi*(780*z+650*z*z))
    for name,a in [('music.wav',bed),('effects.wav',fx)]:
        with wave.open('output/'+name,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes((a.clip(-1,1)*32767).astype('<i2').tobytes())

def main():
    Path('output').mkdir(exist_ok=True);Path('state').mkdir(exist_ok=True)
    plan=prepare()
    if plan is None:print('No fresh verified source; no invented news video.',flush=True);return
    voice=generate(plan['narration'],'output/narration.wav')
    timing_path=Path('output/timing.json')
    timing=json.loads(timing_path.read_text()) if timing_path.exists() else align(plan,voice)
    duration=timing['duration']
    if not 45<=duration<=120:raise ValueError(f'Daily news narration must be 45–120 seconds, got {duration:.1f}')
    Renderer(plan,timing).encode('output/visuals.mp4')
    soundtrack(duration,timing['scenes'])
    normalized=mix_audio(voice,'output/music.wav','output/effects.wav',duration,'output/mix.wav')
    final=Path('output/ai-news-daily.mp4')
    subprocess.run(['ffmpeg','-v','error','-y','-i','output/visuals.mp4','-i','output/mix.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(final)],check=True)
    audit=verify_tail(final,normalized,duration)
    subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],check=True)
    (Path('output')/'verification.json').write_text(json.dumps({'video':str(final),'width':1080,'height':1920,'fps':30,'voice':'Charon','script_model':plan.get('script_model'),'source_url':plan['source']['url'],'source_published':plan['source']['published'],'audio':audit,'automatically_published':False,'editorial_review':plan['editorial_review']},ensure_ascii=False,indent=2))
    safe={**plan,'source':{k:v for k,v in plan['source'].items() if k not in ('article','summary')}}
    (Path('output')/'plan.json').write_text(json.dumps(safe,ensure_ascii=False,indent=2))
    history=Path('state/news_history.json');h=json.loads(history.read_text()) if history.exists() else {'urls':[]}
    h['urls']=list(dict.fromkeys(h['urls']+[plan['source']['url']]))[-500:];history.write_text(json.dumps(h,indent=2))
    print('Verified complete Charon AI news video ready for review.',flush=True)
if __name__=='__main__':main()
