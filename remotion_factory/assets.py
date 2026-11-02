"""Download only authored, licensed source assets and retain their exact evidence."""
import base64,hashlib,json,shutil
from pathlib import Path
import requests
from PIL import Image
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 root=Path('remotion_motion');public=root/'public';public.mkdir(parents=True,exist_ok=True)
 story=json.loads(Path('professional_motion/delivery/story.json').read_text());manifest=json.loads((root/'assets.json').read_text())
 required={s['visual']['asset'] for s in story['scenes'] if s.get('visual',{}).get('asset')};evidence=[]
 for item in manifest['assets']:
  if item['file'] not in required:continue
  target=public/item['file'];proof=target.with_suffix('.source.json');target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists() and proof.exists() and json.loads(proof.read_text()).get('output_sha256')==sha(target):evidence.append(json.loads(proof.read_text()));continue
  cache_paths=[root/p for p in item.get('cache_parts',[])]
  cached=bool(cache_paths) and all(p.is_file() for p in cache_paths)
  if cached:
   content=base64.b64decode(''.join(p.read_text().strip() for p in cache_paths),validate=True)
   if hashlib.sha256(content).hexdigest()!=item['cache_sha256']:raise ValueError('Licensed archive cache fingerprint differs')
  else:
   response=requests.get(item['url'],headers={'User-Agent':'ArabicDocumentaryFactory/1.0 (licensed archival production)'},timeout=60);response.raise_for_status();content=response.content
   if hashlib.sha256(content).hexdigest()!=item['original_sha256']:raise ValueError('Archival source bytes changed; refusing a substituted image')
  import io
  with Image.open(io.BytesIO(content)) as image:
   image=image.convert('RGB');image.thumbnail((2200,2200));image.save(target,quality=94)
  record={**item,'output_sha256':sha(target),'verified_cache_used':cached};proof.write_text(json.dumps(record,ensure_ascii=False,indent=2));evidence.append(record)
 if {r['file'] for r in evidence}!=required:raise ValueError('An authored shot has no licensed archival asset')
 if any(s.get('visual',{}).get('kind')=='map' for s in story['scenes']):
  world=public/'world.json';m=manifest['world']
  if not world.exists() or sha(world)!=m['sha256']:
   r=requests.get(m['url'],timeout=45);r.raise_for_status()
   if hashlib.sha256(r.content).hexdigest()!=m['sha256']:raise ValueError('Natural Earth map bytes differ from the pinned source')
   world.write_bytes(r.content)
  shutil.copy2(root/'node_modules/maplibre-gl/dist/maplibre-gl-worker.mjs',public/'maplibre-worker.mjs')
 fonts=public/'fonts';fonts.mkdir(exist_ok=True)
 for weight in ('Regular','Bold'):shutil.copy2('/usr/share/fonts/truetype/noto/NotoSansArabic-'+weight+'.ttf',fonts/('Arabic-'+weight+'.ttf'))
 (public/'assets-evidence.json').write_text(json.dumps({'assets':evidence,'world':manifest['world'],'fonts':'Noto Sans Arabic; SIL Open Font License'},ensure_ascii=False,indent=2)+'\n')
 print('Authored licensed assets verified:',len(evidence))
if __name__=='__main__':main()
