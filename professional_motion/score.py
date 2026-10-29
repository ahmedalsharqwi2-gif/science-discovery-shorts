"""Original 112 BPM electronica score and sync cues, composed for this film.

No reference sound is sampled. Chord changes, melodic arpeggios, bass, drums,
scene swells and stereo echoes are generated deterministically at 48 kHz.
"""
import json,math,wave
from pathlib import Path
import numpy as np
SR=48000


def build(duration,starts,directory,profile="science",reveal_beats=None):
    out=Path(directory);n=math.ceil(duration*SR);music=np.zeros((n,2),np.float32);sfx=np.zeros_like(music)
    rng=np.random.default_rng(2197);bpm={'science':112,'history':104,'horror':94,'news':120}[profile];beat=60/bpm
    def midi(m):return 440*2**((m-69)/12)
    def put(target,audio,at,gain=1,pan=0):
        lo=round(at*SR)
        if lo<0:audio=audio[-lo:];lo=0
        count=min(len(audio),n-lo)
        if count<=0:return
        audio=audio[:count]*gain
        target[lo:lo+count,0]+=audio*np.sqrt((1-pan)/2)
        target[lo:lo+count,1]+=audio*np.sqrt((1+pan)/2)
    def tone(freq,length,kind='pluck'):
        t=np.arange(round(length*SR),dtype=np.float32)/SR
        if kind=='pluck':
            a=(np.sin(2*np.pi*freq*t)+.22*np.sin(2*np.pi*freq*2.002*t)+.08*np.sin(2*np.pi*freq*4*t))*np.exp(-4.7*t)
            a*=np.minimum(1,t/.008)
        elif kind=='pad':
            a=sum(np.sin(2*np.pi*freq*(1+detune)*t) for detune in (-.003,0,.003))/3
            a+=.13*np.sin(2*np.pi*freq*2*t)
            a*=np.minimum(1,t/.6)*np.minimum(1,np.maximum(0,length-t)/.9)
        else:
            a=(np.sin(2*np.pi*freq*t)+.18*np.sin(2*np.pi*freq*2*t))*np.minimum(1,t/.012)*np.exp(-3*t)
        return a.astype(np.float32)
    chords=[(50,57,60,64),(46,53,57,60),(53,60,64,69),(48,55,57,64)]
    if profile=='horror':chords=[(38,45,50,53),(37,44,48,52),(41,48,50,56),(38,45,49,53)]
    elif profile=='history':chords=[(48,55,60,63),(46,53,58,62),(43,50,55,58),(48,55,58,63)]
    bar=beat*4
    for i in range(math.ceil(duration/bar)):
        chord=chords[(i//2)%4];at=i*bar;intensity=.55 if at<4 else .9 if at<duration-6 else .6
        for j,note in enumerate(chord):put(music,tone(midi(note),bar*1.3,'pad'),at,.055*intensity,(j-1.5)*.4)
        pattern=[0,2,1,3,2,1,3,2]
        for k,degree in enumerate(pattern):
            note=chord[degree]+12+(12 if k in (3,7) and i%2 else 0)
            a=tone(midi(note),1.25);pos=at+k*beat/2
            if profile=='horror':a*=.38 if k%2 else .6
            pan=.6*math.sin(i+k*1.3)
            put(music,a,pos,.11*intensity,pan)
            put(music,a,pos+beat*.75,.027*intensity,-pan)
            put(music,a,pos+beat*1.5,.012*intensity,pan)
        for k in (0,1.5,2.5):put(music,tone(midi(chord[0]-12),.7,'bass'),at+k*beat,.17*intensity)
    for k in range(math.ceil(duration/beat)):
        at=k*beat;section=at/max(duration,1)
        if section<.06 or section>.94:continue
        t=np.arange(int(.32*SR),dtype=np.float32)/SR
        freq=48+100*np.exp(-38*t);phase=2*np.pi*(48*t+100/38*(1-np.exp(-38*t)))
        kick=np.sin(phase)*np.exp(-15*t)*np.minimum(1,t/.002)
        if k%4 in (0,2):put(music,kick,at,.23)
        if k%4 in (1,3):
            noise=rng.standard_normal(int(.18*SR)).astype(np.float32)
            high=noise-np.convolve(noise,np.ones(7)/7,mode='same')
            ti=np.arange(len(high))/SR
            snare=high*np.exp(-28*ti)+.25*np.sin(2*np.pi*180*ti)*np.exp(-30*ti)
            put(music,snare,at,.055,.14)
        for half in (0,.5):
            noise=rng.standard_normal(int(.055*SR)).astype(np.float32)
            high=noise-np.convolve(noise,np.ones(11)/11,mode='same');ti=np.arange(len(high))/SR
            put(music,high*np.exp(-70*ti),at+half*beat,.022 if half else .012,-.35 if half else .35)
    cues=[]
    for i,at in enumerate(starts):
        if i==0:continue
        length=.7;t=np.arange(int(length*SR),dtype=np.float32)/SR
        noise=rng.standard_normal(len(t)).astype(np.float32);noise=np.convolve(noise,np.ones(9)/9,mode='same')
        env=np.sin(np.pi*t/length)**2
        swoosh=noise*env*np.sin(2*np.pi*(350*t+900*t*t))
        put(sfx,swoosh,at-.35,.28,(-.5 if i%2 else .5))
        impact=np.sin(2*np.pi*(45*t+17*(1-np.exp(-7*t))))*np.exp(-9*t)
        put(sfx,impact,at,.12)
        cues.append({'type':'scene_swell','at':at})
    for i in range(10):
        at=starts[min(4,len(starts)-1)]+i*.42
        if at>=duration:break
        put(sfx,tone(midi(84+i%4*3),.35),at,.045,math.sin(i)*.7)
    if profile=='horror':
        # Controlled quiet gaps and brief original low impacts create contrast.
        # Narration is never removed, stretched or padded.
        for at in (reveal_beats or []):
            lo=max(0,round((at-.65)*SR));hi=min(n,round((at+.12)*SR))
            if hi>lo:music[lo:hi]*=.10
            t=np.arange(round(.65*SR),dtype=np.float32)/SR
            hit=(np.sin(2*np.pi*(39*t+9*(1-np.exp(-9*t))))+.18*np.sin(2*np.pi*147*t))*np.exp(-9*t)*np.minimum(1,t/.006)
            put(sfx,hit,at,.13)
            cues.append({'type':'measured_horror_reveal','at':at})
    # Smooth intro/outro; final cadence resolves rather than ending mid-beat.
    put(music,tone(midi(62),2.3,'pad'),max(0,duration-2.4),.13)
    ts=np.arange(n)/SR;fade=np.minimum(1,ts/.6)*np.minimum(1,np.maximum(0,duration-ts)/1.2)
    music*=fade[:,None];sfx*=fade[:,None]
    def save(name,data):
        peak=float(np.max(np.abs(data)))
        if peak>.9:data*=.9/peak
        with wave.open(str(out/name),'wb') as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((data*32767).astype('<i2').tobytes())
    out.mkdir(exist_ok=True,parents=True);save('score.wav',music);save('sfx.wav',sfx)
    (out/'score.json').write_text(json.dumps({'bpm':bpm,'original_composition':True,'reference_audio_sampled':False,'cues':cues,'duration':duration},indent=2))


if __name__=='__main__':
    root=Path(__file__).resolve().parent
    p=root/'delivery/timing.json'
    if not p.exists():raise SystemExit('Measured voice timing is required for the final score')
    t=json.loads(p.read_text());build(t['duration'],[s['start'] for s in t['scenes']],root/'output')
