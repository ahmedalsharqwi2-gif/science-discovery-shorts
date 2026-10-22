"""Fail-closed visual sanity audit before external publication.

This is a technical screen: it detects blank, monochrome and frozen output.
It does NOT certify cinematic/artistic quality.
"""
import json
import math
import subprocess
from pathlib import Path

def _probe(path):
    p = subprocess.run(
        ["ffprobe","-v","error","-select_streams","v:0",
         "-show_entries","stream=width,height,avg_frame_rate:format=duration",
         "-of","json",str(path)],capture_output=True,text=True,check=True)
    return json.loads(p.stdout)

def audit(path, report="output/visual_quality.json"):
    path = Path(path)
    if not path.is_file() or path.stat().st_size < 10000:
        raise ValueError("Visual quality gate: missing or undersized video")
    meta = _probe(path)
    stream = meta["streams"][0]
    duration = float(meta["format"]["duration"])
    width, height = int(stream["width"]), int(stream["height"])
    reasons = []
    if width != 1080 or height != 1920:
        reasons.append(f"Expected vertical 1080x1920, got {width}x{height}")
    if duration < 8:
        reasons.append(f"Video too short: {duration:.1f}s")
    # Sample approximately every 5 s. Full-frame RGB sampling avoids dependence
    # on OpenCV, PIL or numpy and catches solid-colour fallbacks.
    cmd = ["ffmpeg","-v","error","-i",str(path),"-vf",
           "fps=1/5,scale=64:112","-pix_fmt","rgb24","-f","rawvideo","-"]
    proc = subprocess.run(cmd,capture_output=True,check=True)
    size = 64 * 112 * 3
    frames = [proc.stdout[i:i+size] for i in range(0,len(proc.stdout)-size+1,size)]
    if len(frames) < 2:
        reasons.append("Not enough decoded video samples")
    stats = []
    for frame in frames:
        pixels = len(frame) // 3
        sums = [sum(frame[c::3]) / pixels for c in range(3)]
        # Only sparse spatial sample required for color variance.
        luma = [(.2126*frame[i]+.7152*frame[i+1]+.0722*frame[i+2])
                for i in range(0,len(frame),36)]
        mean = sum(luma)/len(luma)
        std = math.sqrt(sum((v-mean)**2 for v in luma)/len(luma))
        stats.append({"rgb_mean":[round(c,1) for c in sums],"luma_std":round(std,2)})
    if stats and min(x["luma_std"] for x in stats) < 6:
        reasons.append("One or more near-blank/flat-colour sampled frames")
    if len(frames) > 2:
        diff=[]
        for a,b in zip(frames,frames[1:]):
            diff.append(sum(abs(a[i]-b[i]) for i in range(0,size,18))/(size/18))
        if sum(x < 1.2 for x in diff) / len(diff) > .70:
            reasons.append("More than 70% of sampled intervals are essentially frozen")
    result={"passed":not reasons,"reasons":reasons,"duration":round(duration,2),
            "resolution":[width,height],"samples":len(frames),"sample_stats":stats,
            "note":"Technical visual sanity gate only; not cinematic quality certification."}
    report = Path(report)
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2,ensure_ascii=False))
    if reasons:
        raise ValueError("Visual quality gate rejected video: "+"; ".join(reasons))
    return result
