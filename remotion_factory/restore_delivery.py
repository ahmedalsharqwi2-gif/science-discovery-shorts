"""Rehydrate the original delivery artifact without any synthesis path."""
import hashlib,json,shutil,sys
from pathlib import Path
from .prepare import DELIVERY,read_request
from .state import mutate
def main():
 req=read_request();root=Path(sys.argv[1]);matches=list(root.glob('**/delivery/story.json')) or list(root.glob('story.json'))
 if len(matches)!=1:raise ValueError('Exactly one retained delivery story is required')
 source=matches[0].parent;story=json.loads((source/'story.json').read_text())
 if story['profile']!=req['profile'] or not (source/'narration.wav').is_file():raise ValueError('Original voice artifact missing or belongs to another channel')
 DELIVERY.mkdir(parents=True,exist_ok=True)
 for p in source.iterdir():
  if p.is_file() and p.suffix in ('.json','.wav'):shutil.copy2(p,DELIVERY/p.name)
 sha=hashlib.sha256((DELIVERY/'story.json').read_bytes()).hexdigest()
 def check(data):
  if data['episodes'][req['slot']]['status'] in ('scheduled','published'):raise RuntimeError('This completed slot is already submitted; no repeated rendering or sending')
  if data['episodes'][req['slot']]['story_sha256']!=sha:raise ValueError('Restored story differs from the reserved original')
 mutate(check)
 if not (DELIVERY/'timing.json').exists():
  from .voice_job import main as measure_original
  measure_original()  # WAV exists and was verified: this cannot reach synthesis.
 print('Original delivery restored; no writing or TTS calls requested')
if __name__=='__main__':main()
