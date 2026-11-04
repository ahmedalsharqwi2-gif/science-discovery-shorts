"""Review-only adapter using the preserved Photo Motion camera compositor.

It cannot publish or declare a film artistically approved. The production
contract and its explicit human-approval requirements remain untouched.
"""
import hashlib,json,subprocess,sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'source'))
from photo_motion.engine import Renderer
class ArchiveReview(Renderer):
 def __init__(self):
  self.images={name:Image.open(ROOT/'studio/public/history'/name).convert('RGBA') for name in ['history-lift.jpg','history-old.jpg','history-document.jpg']}
  self.profile={'accent':'#e4bd77'}
def main():
 proof=json.loads((ROOT/'output/history-assets.json').read_text())
 for item in proof:
  p=ROOT/'studio/public/history'/Path(item['file']).name
  if hashlib.sha256(p.read_bytes()).hexdigest()!=item['actual_sha256']:raise ValueError('Archival image changed')
 shots=[{'start':0,'end':5.5,'background':'history-lift.jpg','camera_start':[1.22,-115,-80],'camera_end':[1.12,-70,-40]}, {'start':5.5,'end':10,'background':'history-lift.jpg','camera_start':[1.03,0,0],'camera_end':[1.08,50,20]}, {'start':10,'end':15.14,'background':'history-old.jpg','camera_start':[1.15,-80,-80],'camera_end':[1.07,25,0]}, {'start':15.14,'end':21.5,'background':'history-old.jpg','camera_start':[1.03,0,0],'camera_end':[1.14,-100,25]}, {'start':21.5,'end':25,'background':'history-document.jpg','camera_start':[1.2,70,-80],'camera_end':[1.08,20,0]}, {'start':25,'end':29.02,'background':'history-lift.jpg','camera_start':[1.10,90,0],'camera_end':[1.02,0,0]}]
 renderer=ArchiveReview();out=ROOT/'studio/public/history/base.mp4'
 ff=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x1920','-r','30','-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast','-threads','2','-pix_fmt','yuv420p',str(out)],stdin=subprocess.PIPE)
 try:
  for f in range(round(29.02*30)):
   t=f/30;idx=next((i for i,s in enumerate(shots) if s['start']<=t<s['end']),len(shots)-1);shot=shots[idx];im=renderer.shot(shot,t)
   if idx and t-shot['start']<.18:im=Image.blend(renderer.shot(shots[idx-1],shot['start']),im,(t-shot['start'])/.18)
   if f in [60,480,690]:im.convert('RGB').save(ROOT/'output'/f'history-base-{f}.jpg')
   ff.stdin.write(im.convert('RGB').tobytes())
   if f%150==0:print('Photo Motion review seconds',f/30,flush=True)
  ff.stdin.close()
  if ff.wait():raise RuntimeError('Photo Motion encoding failed')
 except BaseException:ff.kill();ff.wait();raise
 (ROOT/'output/history-photo.json').write_text(json.dumps({'review_only':True,'publishable':False,'engine':'photo_motion.engine.Renderer.shot','shots':shots,'frames':round(29.02*30),'width':1080,'height':1920,'assets_verified':True},indent=2))
if __name__=='__main__':main()
