"""The only supported production entry point; GitHub Actions owns credentials."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from .editor import prepare, preview_plan
from .renderer import MotionRenderer


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def preflight():
    missing = []
    for names in [('GEMINI_TEXT_API_KEY', 'GEMINI_API_KEY'), ('GEMINI_TTS_API_KEY', 'GEMINI_API_KEY')]:
        if not any(os.getenv(n, '').strip() for n in names):
            missing.append(' or '.join(names))
    if missing:
        raise RuntimeError('Missing repository Actions secret: ' + '; '.join(missing))


def produce(profile, preview=False, width=1080, fps=30):
    out = Path('output');out.mkdir(exist_ok=True)
    # A failed new run must never expose a previous run's final video as success.
    final = out / (profile + ('-motion-preview.mp4' if preview else '-motion.mp4'))
    if final.exists():
        raise FileExistsError('Output already exists; use a clean output directory for a new run')
    if preview:
        plan = preview_plan(profile)
        timing = {'duration': 12., 'words': [], 'scenes': [dict(s, start=i*2., end=(i+1)*2.) for i,s in enumerate(plan['scenes'])]}
        MotionRenderer(plan, timing, preview=True).encode(final, width, fps)
        write_json(out/'preview.json', {'profile': profile, 'silent_storyboard': True,
                    'final_production': False, 'video': str(final), 'duration': 12})
        return final
    if width != 1080 or fps != 30:
        raise ValueError('Production must be 1080x1920 at 30fps')
    preflight()
    plan = prepare(profile)
    write_json(out/'plan.json', plan)
    if profile == 'news':
        from voice_provider.client import generate
        from news.render import align
    else:
        from film_factory.voice import generate
        from film_factory.render import align
    from .performance import performance
    if profile == 'horror':
        for scene in plan['scenes']:
            scene['delivery'] = 'tense'
    style = performance(plan) if profile != 'news' else None
    voice = generate(plan['narration'], str(out/'narration.wav'), style) if style else generate(plan['narration'], str(out/'narration.wav'))
    timing = align(plan, voice)
    duration = float(timing['duration'])
    if not 45 <= duration <= 180:
        raise ValueError(f'Complete narration must be 45–180 seconds, got {duration:.2f}')
    # Preserve measured timing and honest interpolation/phrase-alignment metadata.
    write_json(out/'timing.json', timing)
    MotionRenderer(plan, timing).encode(out/'visuals.mp4')
    from film_factory.sound import build
    from film_factory.delivery import mix_audio, verify_tail
    sound = build(duration, timing['scenes'], profile, timing['words'])
    normalized = mix_audio(voice, out/'music.wav', out/'effects.wav', duration, out/'mix.wav')
    staging = out/(profile+'-motion-unverified.mp4')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'visuals.mp4'),'-i',str(out/'mix.wav'),
        '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k',
        '-t',str(duration),'-movflags','+faststart',str(staging)],check=True)
    from visual_quality_gate import audit
    visual = audit(staging)
    audio = verify_tail(staging, normalized, duration)
    subprocess.run(['ffmpeg','-v','error','-i',str(staging),'-f','null','-'],check=True)
    staging.replace(final)
    write_json(out/'verification.json', {'video': str(final), 'profile': profile,
        'renderer': 'procedural-motion-v1', 'dimensions': [1080,1920], 'fps':30,
        'source':plan['source'], 'editorial_review':plan['editorial_review'],
        'visual':visual, 'audio':audio, 'sound':sound, 'voice':'Charon',
        'narration_sha256':hashlib.sha256(plan['narration'].encode()).hexdigest(),
        'automatically_published':False, 'photographic_fallback':False,
        'note':'Technical gates passed; human review of style and facts is still required.'})
    if profile == 'news':
        history = Path('state/news_history.json')
        data=json.loads(history.read_text()) if history.exists() else {'urls':[]}
        data['urls']=list(dict.fromkeys(data['urls']+[plan['source']['url']]))[-500:]
        history.parent.mkdir(exist_ok=True);write_json(history,data)
    return final


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile',choices=['science','history','horror','news'])
    parser.add_argument('--preview',action='store_true',help='Silent 12s motion storyboard; no API requests')
    parser.add_argument('--width',type=int,default=1080,choices=[360,540,1080])
    parser.add_argument('--fps',type=int,default=30,choices=[15,30])
    args=parser.parse_args()
    print(produce(args.profile,args.preview,args.width,args.fps))


if __name__=='__main__':
    main()
