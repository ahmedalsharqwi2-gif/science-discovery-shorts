"""Real provider integration test; no publishing and no fabricated speech."""
import json, os, subprocess, sys
from pathlib import Path
from voice_provider.client import generate
out=Path('charon-integration');out.mkdir(exist_ok=True)
text='دي عينة جديدة من المستودع لاختبار الصوت المصري. سنة أَلْف تِسْعُمِيَّة تَمَانْيَة وَسِتِّين، والارتفاع خَمْسَة وَسِتِّين مِتْر، والمسافة مِيتِين مِتْر. وآخر جملة لازم تتسمع كاملة لحد النهاية.'
p=generate(text,out/'charon.wav')
generate(text,out/'cached-copy.wav')
meta=json.loads(p.with_suffix('.source.json').read_text())
if p.read_bytes()!=(out/'cached-copy.wav').read_bytes():raise ValueError('Cache did not preserve exact narration')
subprocess.run(['ffmpeg','-v','error','-y','-i',str(p),'-c:a','libmp3lame','-b:a','192k',str(out/'charon.mp3')],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(out/'charon.mp3'),'-f','null','-'],check=True)
duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(out/'charon.mp3')]))
if abs(duration-meta['duration'])>.15:raise ValueError('Encoded narration tail duration changed')
(out/'integration.json').write_text(json.dumps({'repository':os.getenv('GITHUB_REPOSITORY'),'voice':meta['voice'],'model':meta['model'],'duration':meta['duration'],'encoded_duration':duration,'exact_cache_verified':True,'publishing_attempted':False,'human_pronunciation_review_required':True},ensure_ascii=False,indent=2))
print('Actual Charon generated; exact cache and encoded duration verified.',flush=True)
