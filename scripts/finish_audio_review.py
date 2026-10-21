"""Re-mix a previously verified photographic artifact, without any provider calls."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from film_factory.sound import build
from film_factory.delivery import mix_audio,verify_tail,probe

def main():
 parser=argparse.ArgumentParser();parser.add_argument('profile',choices=['science','history','horror']);args=parser.parse_args()
 out=Path('output');plan=json.loads((out/'plan.json').read_text());timing=json.loads((out/'timing.json').read_text());voice=out/'narration.wav';source=json.loads((out/'narration.source.json').read_text())
 assert plan['profile']==args.profile
 assert timing['narration_sha256']==hashlib.sha256(plan['narration'].encode()).hexdigest()
 assert source['text']==plan['narration'] and source['sha256']==hashlib.sha256(voice.read_bytes()).hexdigest()
 assert source['voice']=='Charon' and source['fallback_used'] is False
 if timing.get('audio_sha256'):assert timing['audio_sha256']==source['sha256']
 visuals=out/'visuals.mp4';meta=probe(visuals);video=next(s for s in meta['streams'] if s['codec_type']=='video')
 assert (video['width'],video['height'])==(1080,1920)
 duration=timing['duration'];assert abs(float(meta['format']['duration'])-duration)<.06
 sound=build(duration,timing['scenes'],args.profile,timing['words'])
 normalized=mix_audio(voice,out/'music.wav',out/'effects.wav',duration,out/'mix.wav')
 final=out/(args.profile+'-photo-charon.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-i',str(visuals),'-i',str(out/'mix.wav'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(final)],check=True)
 audio=next(s for s in probe(final)['streams'] if s['codec_type']=='audio');assert audio['channels']==2
 audit=verify_tail(final,normalized,duration)
 report=json.loads((out/'verification.json').read_text());report.update(audio=audit,sound=sound,audio_channels=2,sound_revision='spoken-foley-stereo-v1',original_photographic_frames_reused=True,automatically_published=False)
 (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('Verified stereo final sound review:',args.profile,'duration=',duration,'tail correlation=',audit['last_speech_window_correlation'])
if __name__=='__main__':main()
