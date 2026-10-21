"""Normalize to fixed-rate PCM first; never put a look-ahead normalizer inside framesync."""
from pathlib import Path
import json,subprocess

def run(args):subprocess.run(['ffmpeg','-y','-v','error',*map(str,args)],check=True)
def probe(p):return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(p)]))
def mix_audio(narration,music,effects,duration,out):
    out=Path(out);work=out.parent;work.mkdir(parents=True,exist_ok=True)
    voice=work/'voice-normalized.wav';bed=work/'music-normalized.wav'
    run(['-i',narration,'-af','loudnorm=I=-16:TP=-2:LRA=7,aresample=48000','-c:a','pcm_s16le',voice])
    if abs(float(probe(voice)['format']['duration'])-duration)>.001:raise ValueError('Normalizer changed narration duration')
    run(['-stream_loop','-1','-i',music,'-t',duration,'-af',f'atrim=duration={duration},asetpts=PTS-STARTPTS,loudnorm=I=-27:TP=-9:LRA=7,aresample=48000,afade=t=in:d=1.2,afade=t=out:st={duration-2}:d=2','-c:a','pcm_s16le',bed])
    graph='[0:a]asplit=2[voice][control];[2:a]aresample=48000,volume=.65[sfx];[1:a][sfx]amix=inputs=2:duration=longest:normalize=0[env];[env][control]sidechaincompress=threshold=.025:ratio=8:attack=15:release=350[ducked];[voice][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=.94:latency=1[mix]'
    run(['-i',voice,'-i',bed,'-i',effects,'-filter_complex',graph,'-map','[mix]','-c:a','pcm_s16le',out])
    if abs(float(probe(out)['format']['duration'])-duration)>.001:raise ValueError('Mixer truncated audio; do not pad over lost speech')
    return voice

def verify_tail(video,voice,duration):
    import numpy as np
    def pcm(path):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ar','48000','-ac','1','-f','f32le','-']),np.float32)
    meta=probe(video);audio=next(s for s in meta['streams'] if s['codec_type']=='audio');audio_duration=float(audio['duration'])
    if abs(audio_duration-duration)>.06:raise ValueError(f'Audio/video duration mismatch: {audio_duration} versus {duration}')
    a=pcm(voice);b=pcm(video);start=round((duration-4)*48000);stop=round((duration-.3)*48000)
    source=a[start:stop];source=source-source.mean();den=float(np.linalg.norm(source));best=-1
    for lag in range(-960,961,240):
        target=b[start+lag:stop+lag]
        if len(target)!=len(source):continue
        target=target-target.mean();score=float(np.dot(source,target)/(den*np.linalg.norm(target)+1e-12));best=max(best,score)
    if best<.85:raise ValueError(f'Last spoken words missing/changed after mixing: tail correlation {best:.3f}')
    return {'audio_seconds':audio_duration,'video_seconds':duration,'difference_seconds':audio_duration-duration,'last_speech_window_correlation':best,'audio_tail_checked':True,'silence_padding_used_to_hide_lost_speech':False}
