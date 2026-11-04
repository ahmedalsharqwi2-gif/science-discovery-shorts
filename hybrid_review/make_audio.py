"""Two different original review scores, event cues, and speech-first mixing."""
import hashlib,json,math,subprocess,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;SR=48000
def write(path,data):
 with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(np.clip(data*32767,-32767,32767).astype('<i2').tobytes())
def score(profile,duration):
 n=math.ceil(duration*SR);music=np.zeros((n,2),np.float32);sfx=np.zeros_like(music);rng=np.random.default_rng(784 if profile=='science' else 2671);cues=[]
 def put(target,a,at,gain,pan=0):
  start=round(at*SR)
  if start<0:a=a[-start:];start=0
  count=min(n-start,len(a))
  if count<=0:return
  target[start:start+count,0]+=a[:count]*gain*math.sqrt((1-pan)/2);target[start:start+count,1]+=a[:count]*gain*math.sqrt((1+pan)/2)
 def note(midi,length,voice):
  t=np.arange(round(length*SR))/SR;hz=440*2**((midi-69)/12)
  if voice=='mallet':return np.sin(2*np.pi*hz*t+1.2*np.sin(2*np.pi*hz*2*t)*np.exp(-t*15))*np.exp(-t*5)*np.minimum(1,t/.006)
  if voice=='bow':return (np.sin(2*np.pi*hz*t)+.3*np.sin(2*np.pi*hz*2*t)+.12*np.sin(2*np.pi*hz*3*t))*np.minimum(1,t/.8)*np.minimum(1,(length-t)/1.2)
  return np.sin(2*np.pi*hz*t)*np.sin(np.pi*t/length)**2
 if profile=='science':
  bpm=98;beat=60/bpm;melody=[72,79,76,81,79,74,76,71]
  for i in range(math.ceil(duration/beat)):
   if i%8 in [3,7]:continue
   put(music,note(melody[i%8],.85,'mallet'),i*beat,.12,(-.4 if i%2 else .4))
  for i in range(math.ceil(duration/4)):
   put(music,note([48,53,55,50][i%4],3.7,'bow'),i*4,.045)
  for at in [0,4.8,11,17.28,21.8,27.6,32]:
   t=np.arange(round(.22*SR))/SR;drop=np.sin(2*np.pi*(920*t+180*np.log1p(9*t)))*np.exp(-t*27)*np.minimum(1,t/.003);put(sfx,drop,at,.14,math.sin(at)*.4);cues.append({'at':at,'type':'molecular_water_pop'})
  at=17.01;t=np.arange(round(.6*SR))/SR;noise=rng.standard_normal(len(t));noise=np.convolve(noise,np.ones(15)/15,mode='same');put(sfx,noise*np.sin(np.pi*t/.6)**2,at,.13);cues.append({'at':at,'type':'micelle_assembly_sweep'})
  instrumentation=['FM glass mallet','warm low strings','water pops','assembly sweep']
 else:
  bpm=66
  for i,at in enumerate(np.arange(0,duration,5)):
   for degree in [0,7,12]:put(music,note([45,43,41,43][i%4]+degree,6.4,'bow'),at,.065 if degree==0 else .03,(-.3 if degree==7 else .2))
  for at,m in [(3,69),(10,67),(17,65),(25,64)]:put(music,note(m,3.2,'flute'),at,.045,-.25)
  for at in [0,10,15.14,25]:
   t=np.arange(round(1.2*SR))/SR;hit=np.sin(2*np.pi*(48*t+14*(1-np.exp(-t*7))))*np.exp(-t*5)*np.minimum(1,t/.008);put(sfx,hit,at,.16);cues.append({'at':at,'type':'muted_frame_drum'})
  for at in [5.4,21.4]:
   t=np.arange(round(.4*SR))/SR;paper=rng.standard_normal(len(t));paper=np.convolve(paper,np.ones(5)/5,mode='same')*np.sin(np.pi*t/.4)**2;put(sfx,paper,at,.08,.35);cues.append({'at':at,'type':'archival_paper_change'})
  instrumentation=['slow bowed strings','breathy sine flute','muted frame drum','paper rustle']
 t=np.arange(n)/SR;fade=np.minimum(1,t/.3)*np.minimum(1,(duration-t)/.9);music*=fade[:,None];sfx*=fade[:,None]
 return music,sfx,{'profile':profile,'bpm':bpm,'instrumentation':instrumentation,'seed':784 if profile=='science' else 2671,'cues':cues,'original_synthetic_music':True,'reference_recording_sampled':False}
def main():
 for profile in ['science','history']:
  folder=ROOT/'studio/public'/profile;d=json.loads((folder.parent/(profile+'.json')).read_text())['duration'];music,sfx,meta=score(profile,d);write(folder/'music.wav',music);write(folder/'sfx.wav',sfx)
  normalized=folder/'voice-normalized.wav'
  subprocess.run(['ffmpeg','-y','-v','error','-i',str(folder/'voice.wav'),'-af','loudnorm=I=-16:TP=-2:LRA=8,aresample=48000','-ac','2','-ar','48000','-c:a','pcm_s16le',str(normalized)],check=True)
  with wave.open(str(normalized),'rb') as w:
   if w.getframerate()!=SR or w.getnchannels()!=2:raise ValueError('Wrong normalized voice geometry')
   voice=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32).reshape(-1,2)/32768
  n=round(d*SR)
  if len(voice)!=n:raise ValueError('Normalization must retain every source-time sample')
  block=480;count=math.ceil(n/block);level=np.array([np.sqrt(np.mean(voice[i*block:min(n,(i+1)*block)]**2)) for i in range(count)])
  target=np.maximum(.16,1/(1+(level/.025)**2));smooth=np.empty_like(target);gain=1.
  for i,value in enumerate(target):
   coef=math.exp(-.01/(.015 if value<gain else .26));gain=coef*gain+(1-coef)*value;smooth[i]=gain
  envelope=np.interp(np.arange(n),np.arange(count)*block,smooth)
  mixed=voice+music[:n]*envelope[:,None]*.5+sfx[:n]*.45
  peak=float(np.max(np.abs(mixed)));master=min(1,.89/peak) if peak else 1.;write(folder/'mix.wav',mixed*master)
  meta['normalized_voice_frames']=n;meta['final_mix_frames']=n;meta['master_gain']=master;meta['ducking']='10ms RMS envelope, 15ms attack, 260ms release; no sample deletion, lookahead or time shift'
  meta['duration']=d;meta['voice_reused']=True;meta['mix_sha256']=hashlib.sha256((folder/'mix.wav').read_bytes()).hexdigest();(ROOT/'output'/(profile+'-sound.json')).write_text(json.dumps(meta,indent=2));print(profile,meta['instrumentation'],flush=True)
if __name__=='__main__':main()
