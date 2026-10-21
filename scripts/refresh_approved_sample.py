"""Upgrade an approved artifact's motion and mix, preserving actual speech."""
import argparse,json,subprocess
from pathlib import Path
from film_factory.delivery import mix_audio,verify_tail,probe
from film_factory.sound import build
from film_factory.topics import mark_produced

def main():
 parser=argparse.ArgumentParser();parser.add_argument('profile',choices=['science','history','news']);args=parser.parse_args();out=Path('output')
 plan=json.loads((out/'plan.json').read_text());timing=json.loads((out/'timing.json').read_text())
 plan.update(profile=args.profile,documented=True,fiction=False)
 paths=[out/'images'/('scene-%02d.jpg'%(i+1)) for i in range(len(timing['scenes']))]
 if not all(p.is_file() for p in paths):raise ValueError('Complete approved image set is required')
 if args.profile=='news':
  from news.photo_render import PhotoRenderer
  renderer=PhotoRenderer(plan,timing,paths)
 else:
  from film_factory.camera import FilmRenderer
  renderer=FilmRenderer(plan,timing,paths)
 renderer.encode(out/'visuals.mp4');duration=timing['duration'];sound=build(duration,timing['scenes'],args.profile,timing['words'])
 normalized=mix_audio(out/'narration.wav',out/'music.wav',out/'effects.wav',duration,out/'mix.wav')
 final=out/'final_video_full.mp4'
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(out/'visuals.mp4'),'-i',str(out/'mix.wav'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(final)],check=True)
 audio=verify_tail(final,normalized,duration);assert next(x for x in probe(final)['streams'] if x['codec_type']=='audio')['channels']==2
 report=json.loads((out/'verification.json').read_text());report.update(audio=audio,sound=sound,audio_channels=2,motion_revision='spoken-semantics-v2',documented=True,fiction=False,approved_speech_reused=True)
 (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2));mark_produced(plan)
 print('Upgraded approved complete sample:',args.profile,round(duration,2),flush=True)
if __name__=='__main__':main()
