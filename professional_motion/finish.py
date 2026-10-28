"""Mix the complete original narration, composed score and scene cues; verify output."""
import json
import hashlib
import subprocess
from pathlib import Path
from film_factory.delivery import verify_tail, probe
from motion_factory.quality import audit
from professional_motion.score import build
ROOT=Path(__file__).resolve().parent


def run(args):subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True)


def main():
    timing=json.loads((ROOT/'delivery/timing.json').read_text());duration=timing['duration'];out=ROOT/'output'
    story=json.loads((ROOT/'delivery/story.json').read_text())
    if story['topic_key']!=timing.get('topic_key'):raise ValueError('Story and measured timing belong to different topics')
    if timing.get('audio_sha256')!=hashlib.sha256((ROOT/'delivery/narration.wav').read_bytes()).hexdigest():
        raise ValueError('Measured timing belongs to a different audio file')
    render=json.loads((out/'render.json').read_text())
    if not render.get('originalVoice') or render.get('errors') or abs(render['duration']-duration)>.001:
        raise ValueError('Final visuals must use measured original voice timing')
    build(duration,[s['start'] for s in timing['scenes']],out,story['profile'])
    voice=out/'voice-normalized.wav';music=out/'score-normalized.wav';mix=out/'mix.wav'
    run(['-i',ROOT/'delivery/narration.wav','-af','loudnorm=I=-16:TP=-2:LRA=7,aresample=48000','-c:a','pcm_s16le',voice])
    run(['-i',out/'score.wav','-af','loudnorm=I=-23:TP=-5:LRA=9,aresample=48000','-c:a','pcm_s16le',music])
    graph=('[0:a]aformat=channel_layouts=stereo,asplit=2[v][control];'
           '[1:a][control]sidechaincompress=threshold=.035:ratio=4:attack=12:release=220[ducked];'
           '[2:a]volume=.60[fx];[v][ducked][fx]amix=inputs=3:duration=first:normalize=0,alimiter=limit=.88:latency=1[mix]')
    run(['-i',voice,'-i',music,'-i',out/'sfx.wav','-filter_complex',graph,'-map','[mix]','-ar','48000','-c:a','pcm_s16le',mix])
    if abs(float(probe(mix)['format']['duration'])-duration)>.002:raise ValueError('Mix changed narration duration')
    staging=out/'film-unverified.mp4'
    run(['-i',out/'visuals.mp4','-i',mix,'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','256k',
         '-t',duration,'-movflags','+faststart',staging])
    visuals=audit(staging,timing['scenes'],out/'visual-quality.json')
    audio=verify_tail(staging,voice,duration)
    run(['-i',staging,'-f','null','-'])
    final=out/'professional-review.mp4';staging.replace(final)
    (out/'verification.json').write_text(json.dumps({'file':str(final.name),'width':1080,'height':1920,'fps':30,
        'duration':duration,'voice':'original Gemini Charon','asr_model':timing.get('asr_model'),
        'independent_asr_word_coverage':timing['coverage'],'visual_gate':visuals,'audio_tail':audio,
        'music':'Original composed score','music_bpm':json.loads((out/'score.json').read_text())['bpm'],'source':story['source'],'topic_key':story['topic_key'],'profile':story['profile'],'editorial_review':story['editorial_review'],
        'render':'Three.js procedural geometry, physical lighting, custom skin shader, layered optical bloom',
        'reference_audio_reused':False,'automatically_published':False,
        'status':'Technical checks passed; artistic judgement requires viewing the complete film.'},ensure_ascii=False,indent=2))
    print(final)


if __name__=='__main__':main()
