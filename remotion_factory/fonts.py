"""Locked font preparation; fetch only an exact, pinned official font."""
import hashlib,shutil,urllib.request
from pathlib import Path
from visual_contract import load_template
ROOT=Path(__file__).resolve().parents[1]
def prepare_fonts():
 t=load_template();font=t['font'];public=ROOT/'remotion_motion/public/fonts';public.mkdir(parents=True,exist_ok=True)
 for weight in ('regular','bold'):
  source=ROOT/font[weight]
  if font.get('sha256'):
   if not source.exists():
    content=urllib.request.urlopen(font['source'],timeout=60).read()
    if hashlib.sha256(content).hexdigest()!=font['sha256']:raise ValueError('Official font changed; substitution forbidden')
    source.parent.mkdir(parents=True,exist_ok=True)
    with source.open('xb') as f:f.write(content)
   if hashlib.sha256(source.read_bytes()).hexdigest()!=font['sha256']:raise ValueError('Font fingerprint mismatch')
  if not source.is_file():raise FileNotFoundError('Required locked font is missing: '+str(source))
  shutil.copy2(source,public/('Arabic-'+weight.title()+'.ttf'))
 return t['font']
if __name__=='__main__':print(prepare_fonts().get('family','Locked Arabic font'))
