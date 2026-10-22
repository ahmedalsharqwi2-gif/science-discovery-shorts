"""Opt-in technical media inspection for completed 9:16 documentary reels.

Checks stream integrity, framerate, duration and audio. Does not judge the
artistic quality of an episode or publish it. No API credentials needed.
Usage: python scripts/verify_cinematic_delivery.py output/science-photo-charon.mp4
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path

def inspect(path, *, maximum_seconds=180.0):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError(path)
    result=subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(path)],
                          capture_output=True,text=True,check=True)
    info=json.loads(result.stdout)
    streams=info.get("streams",[])
    videos=[s for s in streams if s.get("codec_type")=="video"]
    audios=[s for s in streams if s.get("codec_type")=="audio"]
    if len(videos)!=1 or not audios:raise ValueError("Exactly one video and at least one audio stream required")
    v=videos[0];a=audios[0]
    duration=float(info.get("format",{}).get("duration") or 0)
    num,den=(v.get("avg_frame_rate") or "0/1").split("/")
    fps=float(num)/max(1,float(den))
    checks={
      "resolution_1080x1920":(v.get("width"),v.get("height"))==(1080,1920),
      "fps_30":abs(fps-30)<.1,
      "duration_valid":5<duration<=maximum_seconds+.5,
      "stereo_audio":int(a.get("channels",0))==2,
      "video_codec_h264":v.get("codec_name")=="h264",
    }
    # Decode enough to catch corrupt mux/frames, not just valid metadata.
    decoded=subprocess.run(["ffmpeg","-nostdin","-v","error","-xerror","-i",str(path),
          "-map","0:v:0","-f","null","-"],capture_output=True,text=True)
    checks["video_decodes"]=decoded.returncode==0
    return {"path":str(path),"duration":round(duration,3),"fps":round(fps,3),
            "codec":v.get("codec_name"),"checks":checks,"passed":all(checks.values()),
            "decoder_error":decoded.stderr[-300:] if decoded.returncode else ""}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--max-duration",type=float,default=180)
    parser.add_argument("--report",default="output/cinematic_delivery_report.json")
    args=parser.parse_args()
    report=inspect(args.video,maximum_seconds=args.max_duration)
    dest=Path(args.report);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    if not report["passed"]:raise SystemExit(2)
if __name__=="__main__":main()
