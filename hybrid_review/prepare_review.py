"""Prepare two explicitly non-publishable hybrid review excerpts, never TTS/posts."""
import argparse,hashlib,json,shutil,subprocess,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=None
REPO=None
TOOLCHAIN=None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 global OLD,REPO,TOOLCHAIN
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--retained-root',type=Path,required=True,help='Directory containing retained full-delivery/<profile>/professional_motion/delivery');parser.add_argument('--repo-root',type=Path,default=ROOT.parent);parser.add_argument('--toolchain-root',type=Path,help='Existing Remotion toolchain with node_modules/public/media/assets.json');args=parser.parse_args()
 OLD=args.retained_root.resolve();REPO=args.repo_root.resolve();TOOLCHAIN=(args.toolchain_root or REPO/'remotion_motion').resolve()
 studio=ROOT/'studio';public=studio/'public'
 for name in ('node_modules','package.json','package-lock.json','tsconfig.json'):
  target=TOOLCHAIN/name
  if name=='node_modules':
   if not (studio/name).exists():(studio/name).symlink_to(target,target_is_directory=True)
  else:shutil.copy2(target,studio/name)
 shutil.copytree(TOOLCHAIN/'public/fonts',public/'fonts',dirs_exist_ok=True)
 cfg=json.loads((studio/'tsconfig.json').read_text());cfg['compilerOptions']['resolveJsonModule']=True;(studio/'tsconfig.json').write_text(json.dumps(cfg,indent=2))
 # Use the exact current Three.js/Playwright installation, no dependency changes.
 stage=ROOT/'source/professional_motion';stage.mkdir(parents=True,exist_ok=True)
 if not (stage/'node_modules').exists():(stage/'node_modules').symlink_to(REPO/'professional_motion/node_modules',target_is_directory=True)
 (ROOT/'source/package.json').write_text('{"type":"module"}\n')
 for name,start,end in [('science',34.30,68.86),('history',0,29.02)]:
  delivery=OLD/'full-delivery'/name/'professional_motion/delivery'
  story=json.loads((delivery/'story.json').read_text());timing=json.loads((delivery/'timing.json').read_text())
  if sha(delivery/'story.json')!=timing['story_sha256'] or sha(delivery/'narration.wav')!=timing['audio_sha256']:raise ValueError('Original timing binding differs')
  duration=round(end-start,6);dest=public/name;dest.mkdir(exist_ok=True)
  # Exact PCM sample slice: no speed, pitch, synthesis or repeated generation.
  with wave.open(str(delivery/'narration.wav'),'rb') as src:
   rate=src.getframerate();src.setpos(round(start*rate));raw=src.readframes(round(duration*rate));params=src.getparams()
  with wave.open(str(dest/'voice.wav'),'wb') as out:out.setparams(params);out.writeframes(raw)
  captions=[{'text':c['text'],'startMs':round(max(0,c['start']-start)*1000),'endMs':round(min(duration,c['end']-start)*1000),'timestampMs':None,'confidence':None} for c in timing['caption_groups'] if c['end']>start and c['start']<end]
  data={'profile':name,'duration':duration,'title':story['title'],'review_only':True,'publishable':False,'voice_generated':False,'source_audio_sha256':timing['audio_sha256'],'source_story_sha256':timing['story_sha256'],'source_interval':[start,end],'excerpt_audio_sha256':sha(dest/'voice.wav'),'captions':captions,'source':story['source'],'engines':['professional_motion.proceduralDirector + scienceCinema','Remotion'] if name=='science' else ['photo_motion.engine.Renderer.shot','Remotion']}
  
  if name=='science':
   data['captions'][0]['text']='الجزيء '+data['captions'][0]['text'];data['captions'][0]['startMs']=40;data['captions'][-1]['endMs']=round(duration*1000)
  else:
   data['captions'][-1]['text']='توصل لمكانها.';data['captions'][-1]['endMs']=28540
  data['caption_boundary_review']='Corrected retained scene-group bleed at exact measured spoken word boundaries; no ASR or voice regeneration'
  write(public/(name+'.json'),data);write(ROOT/'output'/(name+'-source.json'),data)
  shutil.copy2(delivery/'narration.source.json',ROOT/'output'/(name+'-voice-provenance.json'))
 if not (ROOT/'source/photo_motion/__init__.py').exists():(ROOT/'source/photo_motion/__init__.py').write_text('')
 photos=public/'history';proof=[]
 manifest=json.loads((TOOLCHAIN/'assets.json').read_text())
 for name in ['history-lift','history-old','history-document']:
  item=next(a for a in manifest['assets'] if a['id']==name);src=TOOLCHAIN/'public'/item['file']
  if sha(src)!=item['sha256']:raise ValueError('Archival image differs')
  shutil.copy2(src,photos/(name+'.jpg'));proof.append({**item,'actual_sha256':sha(src)})
 write(ROOT/'output/history-assets.json',proof)
 print('Original PCM excerpts and exact archival asset hashes verified',flush=True)
if __name__=='__main__':main()
