"""Only explicitly mapped real assets; missing/unmapped slots remain digital silence."""
import hashlib,json,math,subprocess,wave
from pathlib import Path
import numpy as np
SR=48000
ROOT=Path(__file__).resolve().parents[1]
FAMILIES={'science':(0,'mapped laboratory cues'),'history':(0,'mapped documentary cues'),'horror':(0,'mapped evidence cues'),'news':(0,'no supplied interface assets; silence'),'stickman':(0,'no supplied mapped assets; silence')}
def build(duration,starts,directory,profile='science',reveal_beats=None,episode_key=None,scene_kinds=None):
 from visual_contract import load_template
 t=load_template()
 if profile!=t['channel']:raise ValueError('Cross-channel audio forbidden')
 out=Path(directory);out.mkdir(exist_ok=True,parents=True)
 if any((out/name).exists() for name in ('score.wav','sfx.wav','score.json')):raise FileExistsError('Audio outputs are immutable')
 n=math.ceil(duration*SR);music=np.zeros((n,2),np.float32);sfx=np.zeros_like(music);cues=[];missing=[]
 mapping=json.loads((ROOT/'config/cinematic_sfx.json').read_text()) if (ROOT/'config/cinematic_sfx.json').exists() else {}
 allowed=set(t.get('sfx_allowlist',[])) if profile=='horror' else {p for p in mapping.values() if p}
 # A cue must be explicitly requested by its mapped semantic name. No universal whoosh.
 for i,at in enumerate(starts):
  kind=(scene_kinds or [''])[min(i,len(scene_kinds or [''])-1)]
  cue=kind if kind in mapping else None
  if profile=='horror' and at in (reveal_beats or []):cue='impact'
  if not cue:continue
  name=mapping.get(cue)
  if not name or name not in allowed or not (ROOT/name).is_file():missing.append({'cue':cue,'asset':name,'silent':True});continue
  path=ROOT/name
  raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','2','-ar',str(SR),'-'])
  a=np.frombuffer(raw,dtype='<f4').reshape(-1,2);lo=round(at*SR);count=min(len(a),n-lo)
  if lo<0 or count<=0:raise ValueError('Cue outside narration')
  sfx[lo:lo+count]+=a[:count]*.12
  cues.append({'type':cue,'at':at,'asset':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 def save(name,a):
  with wave.open(str(out/name),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((np.clip(a,-1,1)*32767).astype('<i2').tobytes())
 save('score.wav',music);save('sfx.wav',sfx)
 (out/'score.json').write_text(json.dumps({'profile':profile,'duration':duration,'sound_identity':FAMILIES[profile][1],'cues':cues,'missing_or_unmapped':missing,'music':'silent: no explicitly approved music asset supplied','synthetic_substitutes':False,'score_sha256':hashlib.sha256((out/'score.wav').read_bytes()).hexdigest()},indent=2)+'\n')
