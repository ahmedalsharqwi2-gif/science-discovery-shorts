"""Verify that the final encoded video preserves the actual end of its narration."""
import argparse,json,subprocess
from pathlib import Path
import numpy as np
RATE=8000

def pcm(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar',str(RATE),'-f','f32le','-'])
    return np.frombuffer(raw,dtype=np.float32).astype(np.float64)

def tail_score(source,target):
    if min(len(source),len(target))<RATE:raise ValueError('Insufficient audio for tail verification')
    blocks=len(source)//800;levels=np.sqrt(np.mean(source[:blocks*800].reshape(blocks,800)**2,axis=1))
    voiced=np.flatnonzero(levels>max(float(levels.max())*.04,.0002))
    if not len(voiced):raise ValueError('Narration contains no measurable speech energy')
    end=min(len(source),int((voiced[-1]+1)*800));start=max(0,end-4*RATE)
    if (len(source)-end)/RATE>2.5:raise ValueError('Narration has an unexplained long silent ending')
    ref=source[start:end];ref=ref-ref.mean();pad=RATE//4
    lo=max(0,start-pad);hi=min(len(target),end+pad);search=target[lo:hi]
    if len(search)<len(ref):raise ValueError('Final audio ends before the last speech window')
    size=1<<(len(search)+len(ref)-2).bit_length()
    corr=np.fft.irfft(np.fft.rfft(search,size)*np.fft.rfft(ref[::-1],size),size)[len(ref)-1:len(search)]
    sums=np.r_[0,np.cumsum(search)];squares=np.r_[0,np.cumsum(search*search)];n=len(ref)
    energy=(squares[n:]-squares[:-n])-(sums[n:]-sums[:-n])**2/n
    denominator=np.sqrt(np.maximum(energy,0)*np.dot(ref,ref))+1e-12
    score=float(np.max(corr/denominator))
    if score<.85:raise ValueError(f'Final spoken ending changed or disappeared after mixing: correlation={score:.3f}')
    return score

def verify(video,reference,report):
    meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]))
    v=next(x for x in meta['streams'] if x['codec_type']=='video');a=next(x for x in meta['streams'] if x['codec_type']=='audio')
    if (v['width'],v['height'])!=(1080,1920):raise ValueError('Delivery must be vertical 1080x1920')
    voice=pcm(reference);final=pcm(video)
    if abs(len(voice)-len(final))/RATE>.2:raise ValueError('Encoded audio duration differs from approved narration')
    score=tail_score(voice,final)
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True)
    result={'passed':True,'video':str(video),'reference':str(reference),'voice_seconds':len(voice)/RATE,'final_audio_seconds':len(final)/RATE,'last_speech_correlation':score,'silence_padding_used_to_hide_missing_voice':False,'pronunciation_guaranteed':False}
    Path(report).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('video');p.add_argument('reference');p.add_argument('--report',default='state/delivery_verification.json');args=p.parse_args();verify(args.video,args.reference,args.report)
