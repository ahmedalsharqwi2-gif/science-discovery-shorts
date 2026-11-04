"""Independent local media/provenance checks; never claims artistic approval."""
import hashlib,json,math,subprocess,wave
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def check(profile):
 data=json.loads((ROOT/'studio/public'/(profile+'.json')).read_text());movie=ROOT/'output'/(profile+'-hybrid-review.mp4');meta=probe(movie);v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
 if (v['width'],v['height'],v['r_frame_rate'])!=(1080,1920,'30/1'):raise ValueError('Video geometry differs')
 if abs(float(v['duration'])-data['duration'])>.04 or abs(float(a['duration'])-data['duration'])>.06:raise ValueError('Excerpt duration differs')
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],check=True)
 source=ROOT/'studio/public'/profile/'voice.wav'
 if sha(source)!=data['excerpt_audio_sha256']:raise ValueError('Retained voice changed')
 with wave.open(str(source),'rb') as w:
  if abs(w.getnframes()/w.getframerate()-(data['source_interval'][1]-data['source_interval'][0]))>.0001:raise ValueError('Source sample range differs')
 for c in data['captions']:
  if not 0<=c['startMs']<c['endMs']<=data['duration']*1000+.1:raise ValueError('Caption outside excerpt')
 comparisons=[]
 for second in ([2,12,23,31] if profile=='science' else [2,8,18,26]):
  p=ROOT/'output'/f'{profile}-encoded-{second}.png';subprocess.run(['ffmpeg','-y','-v','error','-ss',str(second),'-i',str(movie),'-frames:v','1',str(p)],check=True)
  from PIL import Image
  frame=np.asarray(Image.open(p).convert('RGB').resize((108,192)),dtype=np.float32)
  if frame.mean()<8 or frame.std()<8:raise ValueError('Blank or nearly uniform frame')
  comparisons.append({'second':second,'mean':round(float(frame.mean()),2),'std':round(float(frame.std()),2)})
 sound=json.loads((ROOT/'output'/(profile+'-sound.json')).read_text())
 mix=ROOT/'studio/public'/profile/'mix.wav'
 if sha(mix)!=sound['mix_sha256']:raise ValueError('Authored mix changed')
 def pcm(p):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-vn','-ar','16000','-ac','1','-f','f32le','-']),dtype='<f4')
 expected=pcm(mix);encoded=pcm(movie);count=min(len(expected),len(encoded))
 if abs(len(expected)-len(encoded))>1024:raise ValueError('Encoded audio differs in sample count')
 correlation=float(np.corrcoef(expected[:count],encoded[:count])[0,1])
 if not math.isfinite(correlation) or correlation<.98:raise ValueError('Final audio does not match authored mix')
 stats=subprocess.run(['ffmpeg','-v','info','-i',str(movie),'-af','volumedetect','-vn','-f','null','-'],capture_output=True,text=True,check=True).stderr
 levels=[l.strip().split(']')[-1].strip() for l in stats.splitlines() if 'mean_volume:' in l or 'max_volume:' in l]
 report={'profile':profile,'review_only':True,'publishable':False,'production_schedule_changed':False,'provider_generation_calls':0,'publication_calls':0,'engines':data['engines'],'title':data['title'],'movie_sha256':sha(movie),'duration':float(meta['format']['duration']),'width':1080,'height':1920,'full_decode_passed':True,'source':data['source'],'source_audio_sha256':data['source_audio_sha256'],'source_story_sha256':data['source_story_sha256'],'source_interval':data['source_interval'],'excerpt_audio_sha256':sha(source),'raw_voice_sample_count_verified':True,'captions_within_excerpt':True,'visual_samples':comparisons,'encoded_mix_correlation':round(correlation,6),'audio_levels':levels,'sound_design':sound,'artistic_approval':'awaiting owner review'}
 (ROOT/'output'/(profile+'-verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 import sys
 for p in sys.argv[1:] or ['science','history']:check(p)
