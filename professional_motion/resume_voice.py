"""Reuse a same-run original narration delivered over Git after interrupted jobs."""
import json,os,subprocess
from pathlib import Path
p=Path('professional_motion/delivery');branch='refs/heads/codex/professional-review-run-'+os.environ['GITHUB_RUN_ID']
if subprocess.run(['git','ls-remote','--exit-code','origin',branch],capture_output=True).returncode==0:
    subprocess.run(['git','fetch','origin',branch],check=True)
    sha=subprocess.check_output(['git','rev-parse','FETCH_HEAD']).decode().strip()
    meta=subprocess.run(['git','show',sha+':professional_motion/delivery/narration.source.json'],capture_output=True)
    if meta.returncode==0:
        story=json.loads((p/'story.json').read_text());text=' '.join(s['narration'] for s in story['scenes'])
        if json.loads(meta.stdout).get('text')==text:
            wav=subprocess.check_output(['git','show',sha+':professional_motion/delivery/narration.wav'])
            (p/'narration.wav').write_bytes(wav);(p/'narration.source.json').write_bytes(meta.stdout)
            print('Resumed exact original narration; no new TTS call is needed')
