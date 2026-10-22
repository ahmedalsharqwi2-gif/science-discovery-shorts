"""Portable audio-event bridge adapted from the supplied Motion_as_kit timing idea.

Input manifest JSON: {"events":[{"at":1.2,"effect":"whoosh_soft"},...]}.
Place properly licensed MP3/WAV assets in assets/sfx or specify --sfx-dir.
Outputs a stereo SFX WAV; existing production should mix it under narration.
Never embeds tokens, downloads unknown assets, or triggers publication.
"""
from __future__ import annotations
import argparse
import json
import math
import shutil
import subprocess
import wave
from pathlib import Path

PROFILES = {
    "science": {"whoosh_soft", "scan_sweep", "spark_ignite", "ui_tick", "impact_small"},
    "history": {"whoosh_soft", "paper_slide", "projector_click", "impact_small", "riser"},
    "horror": {"whoosh_soft", "reverse_suck", "riser", "impact_small", "scan_sweep"},
    "news": {"whoosh_fast", "ui_blip", "typewriter", "scan_sweep", "impact_small"},
}
ALIASES = {"whoosh_fast": "whoosh_fast", "whoosh_soft": "whoosh_soft",
           "impact_small": "impact_small", "ui_blip": "ui_blip",
           "typewriter": "typewriter", "scan_sweep": "scan_sweep",
           "spark_ignite": "spark_ignite", "paper_slide": "paper_slide",
           "projector_click": "projector_click", "reverse_suck": "reverse_suck",
           "riser": "riser", "ui_tick": "ui_tick"}
RATE = 24000

def render(manifest: Path, sfx_dir: Path, output: Path, profile: str, duration: float):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required")
    if profile not in PROFILES or not 0 < duration <= 180:
        raise ValueError("invalid profile or duration")
    events = json.loads(manifest.read_text(encoding="utf-8")).get("events", [])
    if not isinstance(events, list) or len(events) > 160:
        raise ValueError("invalid number of events")
    length = math.ceil(duration * RATE)
    import array
    left = array.array("f", [0.0]) * length
    right = array.array("f", [0.0]) * length
    accepted, skipped = [], []
    for event in events:
        name = str(event.get("effect", ""))
        at = float(event.get("at", -1))
        if name not in PROFILES[profile] or not math.isfinite(at) or not 0 <= at < duration:
            skipped.append({"event": name, "reason": "invalid profile cue/time"})
            continue
        matches = sorted(sfx_dir.glob(name + "_*.mp3")) + sorted(sfx_dir.glob(name + "_*.wav"))
        if not matches:
            skipped.append({"event": name, "reason": "asset missing"})
            continue
        # Decode event into raw signed 16-bit stereo; never load untrusted scripts.
        proc = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(matches[0]),
            "-t", "3", "-ar", str(RATE), "-ac", "2", "-f", "s16le", "-"],
            capture_output=True, check=True)
        import array as _array
        data = _array.array("h")
        data.frombytes(proc.stdout)
        start = int(at * RATE)
        fade = min(len(data)//2, RATE//15)
        for i in range(min(len(data)//2, length-start)):
            env = min(1.0, i/max(1, fade)) * min(1.0, (len(data)//2-i)/max(1, fade))
            gain = .11 * env
            left[start+i] += gain * data[2*i] / 32768
            right[start+i] += gain * data[2*i+1] / 32768
        accepted.append({"effect": name, "at": at, "asset": matches[0].name})
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(RATE)
        samples = _array.array("h")
        for a, b in zip(left, right):
            samples.append(round(32767 * max(-.9, min(.9, a))))
            samples.append(round(32767 * max(-.9, min(.9, b))))
        wav.writeframes(samples.tobytes())
    return {"accepted": accepted, "skipped": skipped, "output": str(output), "profile": profile}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--sfx-dir", type=Path, default=Path("assets/sfx"))
    p.add_argument("--output", type=Path, default=Path("output/motion_kit_sfx.wav"))
    p.add_argument("--profile", choices=sorted(PROFILES), required=True)
    p.add_argument("--duration", type=float, required=True)
    a = p.parse_args()
    print(json.dumps(render(a.manifest, a.sfx_dir, a.output, a.profile, a.duration), ensure_ascii=False))
if __name__ == "__main__":
    main()
