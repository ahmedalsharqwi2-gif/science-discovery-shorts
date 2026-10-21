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
 instructions=['Perform this ORIGINAL FICTION as the person trapped inside the apartment NOW, recording quietly so the presence behind the door cannot hear. Same Charon voice, Egyptian Arabic. Acting must follow the meaning, not an audiobook. Keep every written word. Audible close-mic voiced whispers, frightened breath, short tense pauses; remain intelligible. No screaming, caricature, music or spoken stage directions. Do not say the scene labels.']
 styles={'tense':'restrained unease, low voice, trying to stay rational','whisper':'close-microphone breathy whisper, scared of being overheard','fear':'voice trembles slightly, short breaths and urgent questioning','panic_whisper':'terrified but suppressing volume, broken breathing and slower hushed words, then freeze briefly','calm':'low intimate voice','curious':'uncertain quiet curiosity'}
 for s in plan['scenes']:instructions.append('Beginning with the EXACT words «'+' '.join(s['narration'].split()[:7])+'», use '+styles[s['delivery']]+'.')
 instructions.append('Do not fade away or omit the final words. Whisper the final complete sentence distinctly, then finish.')
 return '\n'.join(instructions)

def main():
 parser=argparse.ArgumentParser();parser.add_argument('profile',choices=['science','history','horror']);parser.add_argument('--prepare-only',action='store_true');args=parser.parse_args()
 plan=prepare(args.profile);Path('output').mkdir(exist_ok=True)
 Path('output/plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2))
 images=prepare_images(plan)
 if args.prepare_only:return
 voice=generate(plan['narration'],'output/narration.wav',performance(plan))
 p=Path('output/timing.json');digest=hashlib.sha256(plan['narration'].encode()).hexdigest();timing=json.loads(p.read_text()) if p.exists() else None
 if not timing or timing.get('narration_sha256')!=digest:timing=align(plan,voice)
 duration=timing['duration']
 if not 70<=duration<=180:raise ValueError(f'Expected 70–180 seconds of complete speech, got {duration:.2f}')
 FilmRenderer(plan,timing,images).encode('output/visuals.mp4')
 sound=build(duration,timing['scenes'],args.profile)
 normalized=mix_audio(voice,'output/music.wav','output/effects.wav',duration,'output/mix.wav')
 final=Path('output')/(args.profile+'-photo-charon.mp4')
 subprocess.run(['ffmpeg','-v','error','-y','-i','output/visuals.mp4','-i','output/mix.wav','-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t',str(duration),'-movflags','+faststart',str(final)],check=True)
 audit=verify_tail(final,normalized,duration)
 subprocess.run(['ffmpeg','-v','error','-i',str(final),'-f','null','-'],check=True)
 Path('output/verification.json').write_text(json.dumps({'profile':args.profile,'series':plan['series'],'topic_id':plan['topic_id'],'video':str(final),'width':1080,'height':1920,'fps':30,'duration':duration,'voice':'Charon','voice_performance':performance(plan),'generated_images':len(images),'audio':audit,'sound':sound,'script_model':plan['script_model'],'source':plan['source'],'fiction':plan['fiction'],'automatically_published':False},ensure_ascii=False,indent=2))
 print('Verified complete photographic '+args.profile+' sample: '+str(final),flush=True)
if __name__=='__main__':main()
