"""Generate Egyptian narration independently of legacy TTS dependencies."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
import numpy as np
import soundfile as sf
import torch
from voicetut_tts import VoiceTutTTS
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument("--request",required=True);a=p.parse_args()
    req=json.loads(Path(a.request).read_text());c=req["config"];out=Path(req["output"])
    out.parent.mkdir(parents=True,exist_ok=True);torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(c["seed"])
    started=time.time();tts=VoiceTutTTS.from_pretrained(c["model"],device="cpu",dtype="float32",language=c["language"])
    if c["speaker"] not in [s.speaker_name for s in tts.list_speakers()]:raise ValueError("Accepted speaker is unavailable")
    normalized=tts.normalizer.normalize(req["text"],language=c["language"])
    wav_path=out if out.suffix.lower()==".wav" else out.with_suffix(".voicetut.wav")
    tts.synthesize(req["text"],speaker=c["speaker"],language=c["language"],speed=c["speed"],num_step=c["num_step"],guidance_scale=c["guidance_scale"],output=str(wav_path))
    wave,rate=sf.read(wav_path,always_2d=True);duration=len(wave)/rate
    if not 0<duration<=180 or not np.isfinite(wave).all() or np.max(np.abs(wave))<.001:raise ValueError("Invalid generated narration")
    if out!=wav_path:
        codec=["-c:a","libmp3lame","-b:a","192k"] if out.suffix.lower()==".mp3" else ["-c:a","flac"]
        subprocess.run(["ffmpeg","-y","-v","error","-i",str(wav_path),*codec,str(out)],check=True);wav_path.unlink()
    subprocess.run(["ffmpeg","-v","error","-i",str(out),"-f","null","-"],check=True)
    report={**c,"text":req["text"],"normalized_spoken_text":normalized,"duration":duration,"sample_rate":rate,"device":"cpu","dtype":"float32","generated_audio_sha256":sha(out),"elapsed_seconds":round(time.time()-started,2),"fallback_used":False,"newly_synthesized":True}
    out.with_suffix(".voice.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({"engine":"voicetut","speaker":c["speaker"],"duration":duration,"fallback_used":False}),flush=True)
if __name__=="__main__":main()
