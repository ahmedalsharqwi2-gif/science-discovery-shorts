"""Generate/reuse approved original voice and measure scene/phrase timing in Actions."""
import hashlib
import json
import subprocess
from pathlib import Path
try:
    from film_factory.voice import generate
except ImportError:
    from voice_provider.client import generate as basic_generate
    def generate(text,path,performance=None):return basic_generate(text,path)
from .alignment import measured_timing


def main():
    root=Path('professional_motion');story=json.loads((root/'delivery/story.json').read_text());out=root/'delivery';out.mkdir(exist_ok=True)
    full=' '.join(s['narration'] for s in story['scenes']);wav=out/'narration.wav';source=out/'narration.source.json'
    if wav.exists():
        if not source.exists() or json.loads(source.read_text()).get('text')!=full:
            raise ValueError('Cached review voice does not match the complete current script')
    else:
        generate(full,str(wav),{'science':'Egyptian Arabic engaging science explanation. ','history':'Egyptian Arabic cinematic historical explanation, clear grounded delivery. ','horror':'Egyptian Arabic gripping horror storyteller. Natural resonant Charon voice with exceptionally clear everyday Egyptian diction. Calm controlled tension and short uneasy pauses, escalating urgency near reveals. Do not whisper, mumble, distort words, scream, add words or swallow sentence endings. Read every supplied word exactly. ','news':'Egyptian Arabic energetic AI-news storyteller with witty dry meme punchlines. Clear facts, natural comedic timing, never a solemn news bulletin. '}[story['profile']]+
                 'Start with curiosity, build momentum, thoughtful final payoff. No music or sound effects. '
                 'Read only the supplied words. Finish the last sentence. Clear natural pace.')
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]))
    from .policy import require_duration
    require_duration(duration)
    from faster_whisper import WhisperModel
    transcripts=[];timing=None
    for name in ('medium','small','large-v3'):
        model=WhisperModel(name,device='cpu',compute_type='int8',cpu_threads=2)
        segments,_=model.transcribe(str(wav),language='ar',word_timestamps=True,beam_size=5,vad_filter=False)
        actual=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in segments for w in s.words or []]
        transcripts.append((name,actual));(out/('asr-'+name+'.json')).write_text(json.dumps({'recognized_words':actual},ensure_ascii=False,indent=2))
        del model
        try:timing=measured_timing(story,duration,transcripts);break
        except ValueError:
            if name=='large-v3':raise
    timing['story_sha256']=hashlib.sha256((root/'delivery/story.json').read_bytes()).hexdigest()
    timing['audio_sha256']=hashlib.sha256(wav.read_bytes()).hexdigest()
    (out/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2))
    timing['profile']=story['profile'];timing['topic_key']=story['topic_key']
    (out/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2))
    print('Original voice measured; exact-token coverage',round(timing['coverage'],3))


if __name__=='__main__':
    try:main()
    except Exception as error:
        out=Path('professional_motion/delivery');out.mkdir(exist_ok=True)
        (out/'error.json').write_text(json.dumps({'error_class':type(error).__name__,'stage':'voice-or-alignment'}))
        raise
