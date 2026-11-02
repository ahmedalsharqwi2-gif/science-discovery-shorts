import hashlib,json,os,subprocess
from pathlib import Path
try:
 from film_factory.voice import generate
except ImportError:
 from voice_provider.client import generate as basic_generate
 def generate(text,path,performance=None):return basic_generate(text,path)
from .prepare import read_request,DELIVERY
from .state import mutate
from .alignment import measured_timing
from .speech_characters import character_timing
from .speech_lexicon import recognized_key
def main():
 req=read_request();story=json.loads((DELIVERY/'story.json').read_text());full=' '.join(s['narration'] for s in story['scenes']);wav=DELIVERY/'narration.wav';source=DELIVERY/'narration.source.json'
 def started(data):
  e=data['episodes'][req['slot']]
  if not wav.exists() and e['status'] in ('voice_requested','voice_ready'):raise RuntimeError('A voice request already exists; restore it instead of synthesizing again')
  if not wav.exists():e.update(status='voice_requested',voice_request_run=int(os.environ['GITHUB_RUN_ID']))
 mutate(started)
 if wav.exists():
  if not source.exists() or json.loads(source.read_text()).get('text')!=full:raise ValueError('Retained voice text differs')
 else:
  style={'science':'Clear engaging Egyptian Arabic science explanation.','history':'Natural Egyptian Arabic true historical storytelling; grounded, curious, cinematic, never grandiose.','horror':'Clear resonant Egyptian Arabic true-disaster storytelling, restrained dread and narrative tension; no whispering, screams, fake dialogue or swallowed words.','news':'Quick Egyptian Arabic technology news with light dry humor, clear facts and natural conversational delivery.','stickman':'Playful Egyptian Arabic what-if story with character actions, setbacks and a comic payoff.'}[story['profile']]
  generate(full,str(wav),style+' Read only the supplied words. Finish the final sentence. No music or sound effects. Natural clear pace without stretching.')
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(wav)]))
 minimum=60 if story['profile']=='news' else 90
 if not minimum<duration<180:raise ValueError(f'Actual voice must be strictly over{minimum}seconds and under180; no padding or speed change')
 from faster_whisper import WhisperModel
 transcripts=[];timing=None;best_exact=0
 for name in ('medium','small','large-v3'):
  p=DELIVERY/('asr-'+name+'.json')
  if p.exists():actual=json.loads(p.read_text())['recognized_words']
  else:
   model=WhisperModel(name,device='cpu',compute_type='int8',cpu_threads=2)
   segments,_=model.transcribe(str(wav),language='ar',word_timestamps=True,beam_size=5,vad_filter=False)
   actual=[{'text':w.word.strip(),'start':float(w.start),'end':float(w.end)} for s in segments for w in s.words or []];del model
   p.write_text(json.dumps({'recognized_words':actual},ensure_ascii=False,indent=2))
  transcripts.append((name,actual))
  try:
   candidate=measured_timing(story,duration,transcripts,allow_low_coverage=True);best_exact=max(best_exact,candidate.get('exact_token_coverage',candidate['coverage']))
   if candidate['coverage']>=.9 and not candidate.get('diagnostic_only'):timing=candidate;break
  except ValueError:pass
  try:timing=character_timing(story,duration,transcripts,recognized_key,best_exact);break
  except ValueError:pass
 if timing is None:raise ValueError('Independent ASR does not cover enough real speech; original voice retained')
 timing.update(story_sha256=hashlib.sha256((DELIVERY/'story.json').read_bytes()).hexdigest(),audio_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),profile=story['profile'],topic_key=story['topic_key'])
 (DELIVERY/'timing.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2)+'\n')
 def ready(data):data['episodes'][req['slot']].update(status='voice_ready',duration=duration,audio_sha256=timing['audio_sha256'],timing_sha256=hashlib.sha256((DELIVERY/'timing.json').read_bytes()).hexdigest(),coverage=timing['coverage'])
 mutate(ready);print(json.dumps({'duration':duration,'coverage':timing['coverage'],'profile':story['profile']}))
if __name__=='__main__':main()
