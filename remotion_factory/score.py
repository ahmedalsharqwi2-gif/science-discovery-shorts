"""Five distinct original scores and semantic cues, varied by retained topic hash."""
import hashlib,json,math,wave
from pathlib import Path
import numpy as np
SR=48000
FAMILIES={'science':(98,'glass mallets and warm low strings'),'history':(66,'bowed strings, flute and frame drum'),'horror':(58,'low drone, sparse piano and creaks'),'news':(114,'dry electronic percussion and short bass pulse'),'stickman':(126,'pizzicato, playful bass and physical comedy accents')}
def build(duration,starts,directory,profile='science',reveal_beats=None,episode_key=None,scene_kinds=None):
 out=Path(directory);out.mkdir(exist_ok=True,parents=True);key=episode_key or profile+':'+str(duration);seed=int(hashlib.sha256(key.encode()).hexdigest()[:8],16);rng=np.random.default_rng(seed);transpose=int(seed%5)-2;bpm=FAMILIES[profile][0]+int(seed%7)-3;beat=60/bpm;n=math.ceil(duration*SR);music=np.zeros((n,2),np.float32);sfx=np.zeros_like(music);cues=[]
 def put(target,a,at,gain,pan=0):
  lo=round(at*SR)
  if lo<0:a=a[-lo:];lo=0
  count=min(len(a),n-lo)
  if count<=0:return
  a=a[:count]*gain;target[lo:lo+count,0]+=a*math.sqrt((1-pan)/2);target[lo:lo+count,1]+=a*math.sqrt((1+pan)/2)
 def tone(note,length,kind):
  t=np.arange(round(length*SR))/SR;hz=440*2**((note+transpose-69)/12)*(1+(seed%997)/100000)
  if kind=='glass':return np.sin(2*np.pi*hz*t+1.1*np.sin(2*np.pi*hz*2*t)*np.exp(-t*15))*np.exp(-5*t)*np.minimum(1,t/.006)
  if kind=='pluck':return (np.sin(2*np.pi*hz*t)+.28*np.sin(2*np.pi*hz*2*t))*np.exp(-t*8)*np.minimum(1,t/.004)
  if kind=='bow':return (np.sin(2*np.pi*hz*t)+.24*np.sin(2*np.pi*hz*2*t)+.1*np.sin(2*np.pi*hz*3*t))*np.minimum(1,t/.7)*np.minimum(1,(length-t)/1)
  if kind=='flute':return np.sin(2*np.pi*hz*t+.012*np.sin(t*31))*np.sin(np.pi*t/length)**2
  return np.sin(2*np.pi*hz*t)*np.exp(-4*t)*np.minimum(1,t/.01)
 if profile=='science':
  melody=[72,79,76,81,79,74,76,71]
  for i in range(math.ceil(duration/beat)):
   if i%8 not in (3,7):put(music,tone(melody[(i+seed%8)%8],.85,'glass'),i*beat,.11,(-.4 if i%2 else .4))
  for i,at in enumerate(np.arange(0,duration,4)):put(music,tone([48,53,55,50][i%4],3.8,'bow'),at,.045)
 elif profile=='history':
  for i,at in enumerate(np.arange(0,duration,5)):
   for degree in (0,7,12):put(music,tone([45,43,41,43][i%4]+degree,6.4,'bow'),at,.055 if not degree else .027,.2 if degree%2 else -.25)
  for i,at in enumerate(np.arange(3,duration,7)):put(music,tone([69,67,65,64][i%4],3.2,'flute'),at,.04)
 elif profile=='horror':
  for i,at in enumerate(np.arange(0,duration,7)):
   put(music,tone([33,32,35,31][i%4],8,'bow'),at,.065,-.2);put(music,tone([45,44,47,43][i%4],7,'bow'),at,.02,.3)
   if i%2:put(music,tone(72+i%3,2.8,'glass'),at+2,.027,.5)
 elif profile=='news':
  for i in range(math.ceil(duration/beat)):
   put(music,tone([45,45,48,43][i%4],.25,'bass'),i*beat,.10)
   t=np.arange(round(.07*SR))/SR;tick=rng.standard_normal(len(t))*np.exp(-t*80)
   if i%2:put(music,tick,i*beat,.025,.2)
   if i%8 in (0,3):put(music,tone([76,79,81,74][i%4],.32,'glass'),i*beat,.055,-.35)
 else:
  for i in range(math.ceil(duration/beat)):
   put(music,tone([60,67,64,69,65,72,67,62][(i+seed%8)%8],.4,'pluck'),i*beat,.11,.4 if i%2 else -.4)
   if i%2==0:put(music,tone([36,41,43,38][i//4%4],.35,'bass'),i*beat,.13)
 for i,at in enumerate(starts):
  kind=(scene_kinds or [''])[min(i,len(scene_kinds or [''])-1)];t=np.arange(round(.7*SR))/SR
  if profile=='science':
   if kind in ('micelle','surfactant','molecule','cell','bacterium'):
    cue=np.sin(2*np.pi*(920*t+180*np.log1p(9*t)))*np.exp(-t*27)*np.minimum(1,t/.003);name='molecular_pop'
   else:cue=tone(83+i%4,.22,'glass');name='mechanism_click'
   put(sfx,cue,at,.13,.3 if i%2 else -.3)
  elif profile=='history':
   noise=rng.standard_normal(len(t));noise=np.convolve(noise,np.ones(7)/7,mode='same')*np.sin(np.pi*t/.7)**2;put(sfx,noise,at,.07,.2);name='archive_paper'
   if i%3==0:put(sfx,np.sin(2*np.pi*(48*t+14*(1-np.exp(-t*7))))*np.exp(-t*6),at,.10)
  elif profile=='horror':
   creak=np.sin(2*np.pi*(180*t+40*t*t))*(.6+.4*np.sin(t*49))*np.exp(-t*4)*np.minimum(1,t/.04);put(sfx,creak,at,.055,-.3);name='restrained_environment_creak'
  elif profile=='news':put(sfx,tone(85,.09,'pluck'),at,.11,.2);name='interface_tick'
  else:
   put(sfx,tone([77,72,84,65,81,79,88,70][i%8],.25,'pluck'),at,.13,.2);name='physical_comedy_accent'
   if i in (2,3):
    until=starts[i+1] if i+1<len(starts) else duration
    for step in np.arange(at,until,.33):put(sfx,tone(40,.065,'bass'),step,.09,.2 if int(step*3)%2 else -.2)
  cues.append({'type':name,'at':at,'scene_object':kind})
 if profile=='horror':
  for at in reveal_beats or starts[2::3]:
   lo=max(0,round((at-.6)*SR));hi=min(n,round((at+.12)*SR));music[lo:hi]*=.08;cues.append({'type':'music_only_silence_before_reveal','at':at,'narration_untouched':True})
 t=np.arange(n)/SR;fade=np.minimum(1,t/.4)*np.minimum(1,np.maximum(0,duration-t)/1.1);music*=fade[:,None];sfx*=fade[:,None]
 def save(name,data):
  peak=float(np.max(np.abs(data)))
  if peak>.85:data*=.85/peak
  with wave.open(str(out/name),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((data*32767).astype('<i2').tobytes())
 save('score.wav',music);save('sfx.wav',sfx)
 (out/'score.json').write_text(json.dumps({'profile':profile,'bpm':bpm,'sound_identity':FAMILIES[profile][1],'seed':seed,'episode_key_sha256':hashlib.sha256(key.encode()).hexdigest(),'duration':duration,'cues':cues,'original_composition':True,'reference_audio_sampled':False,'score_sha256':hashlib.sha256((out/'score.wav').read_bytes()).hexdigest()},indent=2)+'\n')
