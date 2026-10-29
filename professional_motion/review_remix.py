"""Repository-run review remix: preserve every video frame and the original voice."""
import hashlib,json,os,subprocess
from pathlib import Path
from .finish import run
from .score import build
from film_factory.delivery import verify_tail,probe
from motion_factory.quality import audit
ROOT=Path('professional_motion');OUT=ROOT/'output';DELIVERY=ROOT/'delivery'

def read_ref(ref,names):
 subprocess.run(['git','fetch','origin','refs/heads/'+ref,'--depth=1'],check=True)
 sha=subprocess.check_output(['git','rev-parse','FETCH_HEAD']).decode().strip()
 return {name:subprocess.check_output(['git','show',sha+':'+path]) for name,path in names.items()}

def main():
 config=json.loads(Path('config/review_remix_inputs.json').read_text());profile=config['profile']
 OUT.mkdir(exist_ok=True);DELIVERY.mkdir(exist_ok=True)
 files={'video':config['video_path']}
 if config.get('report_path'):files['report']=config['report_path']
 media=read_ref(config['video_ref'],files)
 evidence=read_ref(config['evidence_ref'],{name:'professional_motion/delivery/'+name for name in ('timing.json','narration.wav','narration.source.json')})
 for name,data in evidence.items():(DELIVERY/name).write_bytes(data)
 timing=json.loads(evidence['timing.json']);duration=timing['duration'];voice_sha=hashlib.sha256(evidence['narration.wav']).hexdigest()
 if timing.get('audio_sha256')!=voice_sha:raise ValueError('Measured timing must match the original unchanged narration')
 original=OUT/'original-review.mp4';original.write_bytes(media['video'])
 voice=OUT/'voice-normalized.wav';music=OUT/'score-normalized.wav';mix=OUT/'mix.wav'
 run(['-i',DELIVERY/'narration.wav','-af','loudnorm=I=-16:TP=-2:LRA=7,aresample=48000','-c:a','pcm_s16le',voice])
 verify_tail(original,voice,duration)
 build(duration,[s['start'] for s in timing['scenes']],OUT,profile)
 run(['-i',OUT/'score.wav','-af','loudnorm=I=-27:TP=-5:LRA=9,aresample=48000','-c:a','pcm_s16le',music])
 graph=('[0:a]aformat=channel_layouts=stereo,asplit=2[v][control];[1:a][control]sidechaincompress=threshold=.035:ratio=4:attack=12:release=220[ducked];[2:a]volume=.60[fx];[v][ducked][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=.88:latency=1[mix]')
 run(['-i',voice,'-i',music,'-i',OUT/'sfx.wav','-filter_complex',graph,'-map','[mix]','-ar','48000','-c:a','pcm_s16le',mix])
 final=OUT/'professional-review.mp4'
 run(['-i',original,'-i',mix,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','256k','-t',duration,'-movflags','+faststart',final])
 def picture_hash(path):return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v','-c:v','copy','-f','hash','-hash','sha256','-']).decode().strip()
 if picture_hash(original)!=picture_hash(final):raise ValueError('Music-only remix must preserve every original video packet')
 report=json.loads(media['report']) if 'report' in media else json.loads(Path(config['legacy_report_path']).read_text())
 report.update(profile=profile,topic_key=config['topic_key'],duration=duration,visual_gate=audit(final,timing['scenes'],OUT/'visual-quality.json'),audio_tail=verify_tail(final,voice,duration),music_target_lufs=-27,music_reduction_db=4,voice_regenerated=False,video_frames_unchanged=True,original_voice_sha256=voice_sha,automatically_published=False)
 run(['-i',final,'-f','null','-'])
 (OUT/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('Original voice and all video frames preserved; music lowered by 4 dB')

if __name__=='__main__':main()
