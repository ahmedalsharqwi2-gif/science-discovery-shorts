"""Use the retained Photo Motion camera on verified assets; no voice or publishing."""
import hashlib,json,math,subprocess
from pathlib import Path
from PIL import Image
from photo_motion.engine import Renderer
class BoundPhotoCamera(Renderer):
 def __init__(self,path):self.images={'image':Image.open(path).convert('RGBA')};self.profile={'accent':'#edc37a'}
def render(story,timing,plan,public):
 if story['profile'] not in ('history','horror'):return
 folder=public/'identity-backgrounds';folder.mkdir(exist_ok=True);photo_frames=[]
 for i,(scene,measured) in enumerate(zip(plan['scenes'],timing['scenes'])):
  if not scene.get('asset'):continue
  source=(public/scene['asset']).resolve()
  if not source.is_relative_to(public.resolve()) or not source.is_file():raise ValueError('Invalid bound photo path')
  digest=hashlib.sha256(source.read_bytes()).hexdigest();duration=measured['end']-measured['start'];frames=(math.ceil(timing['duration']*30) if i==len(plan['scenes'])-1 else round(measured['end']*30))-round(measured['start']*30)
  signature=hashlib.sha256(f'{digest}:{duration}:{frames}:{i}:photo-camera-v1'.encode()).hexdigest()[:20];name=signature+'.mp4';target=folder/name;proof=target.with_suffix('.json')
  if proof.exists() and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==json.loads(proof.read_text()).get('sha256'):
   scene['background_clip']='identity-backgrounds/'+name;continue
  camera=BoundPhotoCamera(source);spec={'start':0,'end':duration,'background':'image','camera_start':[1.04,(-1 if i%2 else 1)*45,-25],'camera_end':[1.13,(-1 if i%2 else 1)*-35,20]}
  ff=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','720x1280','-r','30','-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','20','-threads','2','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
  try:
   for frame in range(frames):ff.stdin.write(camera.shot(spec,frame/30).convert('RGB').resize((720,1280),Image.Resampling.BILINEAR).tobytes())
   ff.stdin.close()
   if ff.wait():raise RuntimeError('Photo Motion background encoder failed')
  except BaseException:ff.kill();ff.wait();raise
  data={'engine':'photo_motion.engine.Renderer.shot','source_sha256':digest,'frames':frames,'duration':duration,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'human_approval_claimed':False,'voice_or_publication_calls':0}
  proof.write_text(json.dumps(data,indent=2));scene['background_clip']='identity-backgrounds/'+name;photo_frames.append(data);print('Photo Motion shot',i+1,'bound to',digest[:10],flush=True)
 plan['photo_motion_backgrounds']=photo_frames
