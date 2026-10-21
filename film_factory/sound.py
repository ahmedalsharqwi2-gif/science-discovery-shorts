"""Original stereo Foley, scene-specific cues, no stock music dependency."""
import math,wave
from pathlib import Path
import numpy as np

def pan(x,p):return np.stack((x*np.sqrt((1-p)/2),x*np.sqrt((1+p)/2)),axis=-1)
def write(path,data,rate):
 with wave.open(str(path),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes((np.clip(data,-.95,.95)*32767).astype('<i2').tobytes())
def build(duration,scenes,profile):
 rate=24000;n=math.ceil(duration*rate);t=np.arange(n,dtype=np.float32)/rate;rng=np.random.default_rng(773)
 bed=np.zeros((n,2),dtype=np.float32);fx=np.zeros_like(bed);events=[]
 if profile=='horror':
  base=.008*np.sin(2*np.pi*43*t)+.005*np.sin(2*np.pi*58.7*t)+.003*np.sin(2*np.pi*86.1*t)
  base*=.6+.4*np.sin(t*.11)**2;bed+=pan(base,.3*np.sin(t*.08))
 else:
  for k,f in enumerate((110,164.81,220)):
   bed+=pan(.012*np.sin(2*np.pi*f*t)*(.6+.25*np.sin(t/(5+k))),(-.2+k*.2))
 def put(at,length,kind,p=0):
  lo=max(0,round(at*rate));hi=min(n,lo+round(length*rate))
  if hi<=lo:return
  z=np.arange(hi-lo,dtype=np.float32)/rate;noise=rng.standard_normal(len(z)).astype(np.float32)
  if kind=='knock':a=.16*(np.sin(2*np.pi*165*z)+.3*np.sin(2*np.pi*390*z))*np.exp(-35*z)+.025*noise*np.exp(-70*z)
  elif kind=='footsteps':a=.055*noise*np.exp(-30*z)+.08*np.sin(2*np.pi*90*z)*np.exp(-24*z)
  elif kind=='latch':a=.045*noise*np.exp(-16*z)+.035*np.sin(2*np.pi*(640*z-180*z*z))*np.exp(-11*z)
  elif kind=='heartbeat':a=.045*np.sin(2*np.pi*57*z)*np.exp(-20*z)+.025*np.sin(2*np.pi*65*z)*np.exp(-30*np.abs(z-.15))
  elif kind=='embers':a=.018*noise*np.exp(-3*z)+.02*np.sin(2*np.pi*65*z)*np.exp(-2*z)
  elif kind=='firebreak':a=.07*noise*np.exp(-5*z)+.05*np.sin(2*np.pi*60*z)*np.exp(-4*z)
  else:a=.025*np.sin(2*np.pi*(420*z+180*z*z))*np.exp(-10*z)
  # Short reflected tail on the environment only, never on speech.
  echo=round(.085*rate)
  if len(a)>echo:a[echo:]+=.23*a[:-echo]
  fx[lo:hi]+=pan(a,p)
 for i,s in enumerate(scenes):
  kind=s.get('effect','none');at=s['beat'];p=(-.65 if i%2 else .65)
  if kind=='silence':
   a=max(0,round((at-.25)*rate));b=min(n,round((at+1.4)*rate));bed[a:b]*=.06;events.append({'kind':kind,'at':at,'cue':s['cue']});continue
  if kind=='none':continue
  for j,offset in enumerate((0,.42) if kind=='knock' else (0,.75,1.5) if kind=='footsteps' else (0,1.1,2.2) if kind=='heartbeat' else (0,)):
   put(at+offset,.8 if kind!='firebreak' else 1.7,kind,p);events.append({'kind':kind,'at':at+offset,'cue':s['cue']})
 fade=np.minimum(1,t/1.3)*np.minimum(1,np.maximum(0,duration-t)/1.5)
 bed*=fade[:,None];fx*=fade[:,None]
 out=Path('output');write(out/'music.wav',bed,rate);write(out/'effects.wav',fx,rate)
 return {'original_synthesized_foley':True,'stereo_environment':True,'events':events,'voice_in_center':True}
