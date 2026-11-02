"""Mix the complete original narration, composed score and scene cues; verify output."""
import json
import argparse
import hashlib
import subprocess
from pathlib import Path
from film_factory.delivery import verify_tail, probe
from motion_factory.quality import audit
from professional_motion.score import build
ROOT=Path(__file__).resolve().parent


def run(args):subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--delivery-dir',type=Path,default=ROOT/'delivery')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'output')
    parser.add_argument('--pipeline',choices=['legacy','v2'],default='v2')
    parser.add_argument('--validation-kind',choices=['fresh','archived-topic'],default='fresh')
    args=parser.parse_args()
    delivery=args.delivery_dir;out=args.output_dir
    timing=json.loads((delivery/'timing.json').read_text());duration=timing['duration']
    requested_story=json.loads((delivery/'story.json').read_text())
    if not ((60<float(duration)<180) if requested_story['profile']=='news' else (90<=float(duration)<180)):
        raise ValueError('Requested news must exceed60seconds; other full films require90seconds; all must stay under180seconds')
    from .policy import require_duration
    require_duration(duration)
    story=json.loads((delivery/'story.json').read_text())
    if story['topic_key']!=timing.get('topic_key'):raise ValueError('Story and measured timing belong to different topics')
    if timing.get('audio_sha256')!=hashlib.sha256((delivery/'narration.wav').read_bytes()).hexdigest():
        raise ValueError('Measured timing belongs to a different audio file')
    story_hash=hashlib.sha256((delivery/'story.json').read_bytes()).hexdigest()
    if timing.get('story_sha256')!=story_hash:raise ValueError('Story changed after voice timing')
    render=json.loads((out/'render.json').read_text())
    if render.get('pipeline','legacy')!=args.pipeline:raise ValueError('Renderer pipeline does not match requested finalizer')
    if render.get('story_sha256')!=story_hash:raise ValueError('Story changed after rendering')
    if not render.get('originalVoice') or render.get('errors') or abs(render['duration']-duration)>.001:
        raise ValueError('Final visuals must use measured original voice timing')
    build(duration,[s['start'] for s in timing['scenes']],out,story['profile'],[s['scare_beat'] for s in timing['scenes'] if 'scare_beat' in s])
    voice=out/'voice-normalized.wav';music=out/'score-normalized.wav';mix=out/'mix.wav'
    run(['-i',delivery/'narration.wav','-af','loudnorm=I=-16:TP=-2:LRA=7,aresample=48000','-c:a','pcm_s16le',voice])
    run(['-i',out/'score.wav','-af','loudnorm=I=-27:TP=-5:LRA=9,aresample=48000','-c:a','pcm_s16le',music])
    graph=('[0:a]aformat=channel_layouts=stereo,asplit=2[v][control];'
           '[1:a][control]sidechaincompress=threshold=.035:ratio=4:attack=12:release=220[ducked];'
           '[2:a]volume=.60[fx];[v][ducked][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=.88:latency=1[mix]')
    run(['-i',voice,'-i',music,'-i',out/'sfx.wav','-filter_complex',graph,'-map','[mix]','-ar','48000','-c:a','pcm_s16le',mix])
    if abs(float(probe(mix)['format']['duration'])-duration)>.002:raise ValueError('Mix changed narration duration')
    staging=out/'film-unverified.mp4'
    run(['-i',out/'visuals.mp4','-i',mix,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','256k',
         '-t',duration,'-movflags','+faststart',staging])
    visuals=audit(staging,timing['scenes'],out/'visual-quality.json')
    require_duration(float(probe(staging)['format']['duration']))
    audio=verify_tail(staging,voice,duration)
    run(['-i',staging,'-f','null','-'])
    final=out/'professional-review.mp4';staging.replace(final)
    (out/'verification.json').write_text(json.dumps({'file':str(final.name),'width':1080,'height':1920,'fps':30,
        'duration':duration,'story_sha256':story_hash,'voice':'original Gemini Charon','asr_model':timing.get('asr_model'),
        'independent_asr_word_coverage':timing['coverage'],'exact_token_coverage':timing.get('exact_token_coverage',timing['coverage']),'speech_matching_method':timing.get('timing_method'),'known_name_normalization_applied':timing.get('known_name_and_egyptian_normalization_applied',False),'visual_gate':visuals,'audio_tail':audio,
        'publication_metadata':__import__('professional_motion.metadata',fromlist=['make']).make(story,story['profile']),'duration_policy':({'minimum_exclusive':60,'maximum_exclusive':180} if story['profile']=='news' else {'minimum_inclusive':90,'maximum_exclusive':180}),'pipeline':args.pipeline,'validation_kind':args.validation_kind,'music_target_lufs':-27,'music':'Original composed score','music_bpm':json.loads((out/'score.json').read_text())['bpm'],'source':story['source'],'topic_key':story['topic_key'],'profile':story['profile'],'editorial_review':story['editorial_review'],
        'render':('Three.js geometry and lighting with reference editorial frame; bloom disabled' if render.get('visual_style')=='reference' else 'Three.js procedural geometry, physical lighting, custom skin shader, layered optical bloom'),
        'visual_style':render.get('visual_style','original'),'review_watermark':bool(render.get('review',False)),
        'reference_audio_reused':args.validation_kind=='archived-topic','automatically_published':False,
        'status':'Technical checks passed; artistic judgement requires viewing the complete film.'},ensure_ascii=False,indent=2))
    print(final)


if __name__=='__main__':main()
