import argparse,hashlib,json,subprocess
from pathlib import Path
from film_factory.editor import prepare
from film_factory.images import prepare_images
from film_factory.voice import generate
from film_factory.render import align
from film_factory.camera import FilmRenderer
from film_factory.sound import build
from film_factory.delivery import mix_audio,verify_tail

def performance(plan):
 if plan['profile']!='horror':return 'Natural Egyptian Arabic, engaging conversational explanation, precise spoken numbers, not a formal announcer. No extra words. Complete the last sentence.'
 instructions=['Same approved Charon voice, natural Egyptian Arabic. DOCUMENTARY about an actual incident, not impersonation of a victim. Low intimate voiced speech, restrained fear and pauses appropriate to the words. Whisper only the narrator emphasis, never invent dialogue or screams. Every word remains clearly voiced; finish the last sentence. No added words, music or spoken directions.']
 styles={'tense':'restrained apprehension, calm control','whisper':'quiet close-mic VOICED emphasis, completely intelligible','fear':'sober concern with short pauses','panic_whisper':'hushed urgent emphasis, voiced consonants, never shout','calm':'clear grounded factual explanation','curious':'quiet investigative curiosity'}
 for scene in plan['scenes']:instructions.append('Beginning with EXACT words «'+' '.join(scene['narration'].split()[:7])+'», use '+styles[scene['delivery']]+'.')
 return '\n'.join(instructions)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('profile',choices=['science','history','horror']);parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 plan=prepare(args.profile);Path('output').mkdir(exist_ok=True)
 Path('output/plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 images=prepare_images(plan)
 if args.prepare_only:return
 voice=generate(plan['narration'],'output/narration.wav',performance(plan))
 p=Path('output/timing.json');digest=hashlib.sha256(plan['narration'].encode()).hexdigest();timing=json.loads(p.read_text()) if p.exists() else None
 voice_digest=hashlib.sha256(Path(voice).read_bytes()).hexdigest()
 if not timing or timing.get('narration_sha256')!=digest or timing.get('audio_sha256')!=voice_digest:
  timing=align(plan,voice);timing['audio_sha256']=voice_digest;p.write_text(json.dumps(timing,ensure_ascii=False,indent=2))
 duration=timing['duration']
 if not 70<=duration<=180:raise ValueError(f'Expected 70–180 seconds of complete speech, got {duration:.2f}')
 FilmRenderer(plan,timing,images).encode('output/visuals.mp4')
 sound=build(duration,timing['scenes'],args.profile,timing['words'])
 normalized=mix_audio(voice,'output/music.wav','output/effects.wav',duration,'output/mix.wav')
 final=Path('output')/(args.profile+'-photo-charon.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-i','output/visuals.mp4','-i','output/mix.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(final)],check=True)
 audit=verify_tail(final,normalized,duration)
 subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],check=True)
 Path('output/verification.json').write_text(json.dumps({'profile':args.profile,'series':plan['series'],'topic_id':plan['topic_id'],'video':str(final),'width':1080,'height':1920,'fps':30,'duration':duration,'voice':'Charon','voice_performance':performance(plan),'generated_images':len(images),'audio':audit,'sound':sound,'script_model':plan['script_model'],'source':plan['source'],'automatically_published':False,'documented':True,'fiction':False,'audio_channels':2,'motion_revision':'spoken-semantics-v2'},ensure_ascii=False,indent=2))
 from film_factory.topics import mark_produced
 mark_produced(plan)
 print('Verified complete photographic '+args.profile+' sample: '+str(final),flush=True)
if __name__=='__main__':main()
