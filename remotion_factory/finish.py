"""Finish only a full Remotion film bound to the same original voice and script."""
import hashlib,json,subprocess
from pathlib import Path
from .prepare import DELIVERY,read_request
from .state import mutate
from .score import build
from .audio_delivery import probe,mix_audio,verify_tail,run
OUT=Path('professional_motion/output')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 req=read_request();story=json.loads((DELIVERY/'story.json').read_text());timing=json.loads((DELIVERY/'timing.json').read_text());render=json.loads((OUT/'render.json').read_text());duration=timing['duration']
 if render.get('pipeline')!='remotion' or render.get('render_mode')!='video' or render.get('review') or render.get('errors') or not render.get('originalVoice'):raise ValueError('Only a completed original-voice Remotion film can finish')
 if render['story_sha256']!=sha(DELIVERY/'story.json') or render['audio_sha256']!=sha(DELIVERY/'narration.wav'):raise ValueError('Source changed after rendering')
 meta=probe(OUT/'visuals.mp4');video=next(s for s in meta['streams'] if s['codec_type']=='video')
 if (video['width'],video['height'])!=(1080,1920) or int(video['nb_frames'])!=render['total_frames']:raise ValueError('Rendered frames or geometry do not cover the full narration')
 build(duration,[s['start'] for s in timing['scenes']],OUT,story['profile'])
 voice=mix_audio(DELIVERY/'narration.wav',OUT/'score.wav',OUT/'sfx.wav',duration,OUT/'mix.wav')
 movie=OUT/'remotion-complete.mp4'
 run(['-i',OUT/'visuals.mp4','-i',OUT/'mix.wav','-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',movie])
 report=probe(movie);actual=float(report['format']['duration']);minimum=60 if story['profile']=='news' else 90
 if not minimum<actual<180 or abs(actual-duration)>.06:raise ValueError('Actual full-film duration differs from approved original speech')
 subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(movie),'-f','null','-'],check=True)
 tail=verify_tail(movie,voice,duration)
 evidence=json.loads(Path('remotion_motion/public/assets-evidence.json').read_text())
 validation={'profile':story['profile'],'topic_key':story['topic_key'],'title':story['title'],'duration':actual,'width':1080,'height':1920,'fps':30,'video_sha256':sha(movie),'story_sha256':sha(DELIVERY/'story.json'),'original_audio_sha256':sha(DELIVERY/'narration.wav'),'speech_coverage':timing['coverage'],'exact_token_coverage':timing.get('exact_token_coverage',timing['coverage']),'audio_tail':tail,'fully_decoded':True,'renderer':render,'licensed_assets':evidence,'true_story_required':story['profile'] in ('history','horror'),'fiction':story.get('fiction',False),'source':story['source'],'review_sample':False,'publication_state':'not_submitted; full visual review still required'}
 (OUT/'remotion-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 (OUT/'credits.json').write_text(json.dumps({'sources':story['source'],'assets':evidence,'music':'Original score composed for this episode','voice':'Original Gemini Charon; current repository credentials'},ensure_ascii=False,indent=2)+'\n')
 def ready(data):data['episodes'][req['slot']].update(status='rendered',video_sha256=validation['video_sha256'],duration=actual,render_run=int(__import__('os').environ['GITHUB_RUN_ID']),source_evidence_file='professional_motion/output/remotion-validation.json')
 mutate(ready);print(json.dumps({'status':'full_film_rendered','duration':actual,'sha256':validation['video_sha256'],'submitted_to_any_platform':False}))
if __name__=='__main__':main()
