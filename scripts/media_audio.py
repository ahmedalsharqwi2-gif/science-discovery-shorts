"""Normalize clip audio layouts and duck scene audio beneath narration."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path


def media_executable(name: str) -> str:
    executable = shutil.which(name)
    if executable is None:
        raise FileNotFoundError(f"Required media tool is missing: {name}")
    return str(Path(executable).resolve())


def has_audio(path: Path) -> bool:
    result = subprocess.run([media_executable("ffprobe"), "-v", "error", "-select_streams", "a:0",
                             "-show_entries", "stream=index", "-of", "json", str(path)],
                            capture_output=True, text=True, check=True)
    return bool(json.loads(result.stdout or "{}").get("streams"))


def normalized_audio_args(path: Path, keep: bool) -> tuple[list[str], list[str]]:
    """Every normalized clip has stereo 48 kHz AAC, including muted clips."""
    if keep and has_audio(path):
        inputs, mapping = [], "0:a:0"
    else:
        inputs = ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        mapping = "1:a:0"
    return inputs, ["-map", mapping, "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "128k"]


def ducking_filters(voice: str, original: str) -> list[str]:
    """Split the narration: sidechain input pads cannot be consumed twice."""
    return [f"{voice}aresample=48000,asplit=2[voice][sidechain]",
            f"{original}aresample=48000,volume=0.18[original]",
            "[original][sidechain]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350:makeup=1[ducked]"]


def add_topic_soundtrack(mixed_audio: Path, narration: Path, duration: float,
                         channel: str, topic: str = "") -> None:
    """Original procedural score: no recordings, third-party samples or downloads."""
    import hashlib
    import math
    import os
    import re
    import struct
    import wave

    if os.getenv("BACKGROUND_MUSIC_ENABLED", "true").lower() != "true":
        return
    if not topic:
        episode_path = Path(__file__).resolve().parent.parent / "state/current_episode.json"
        try:
            episode = json.loads(episode_path.read_text(encoding="utf-8"))
            topic = str(episode.get("title", "")) + " " + str(episode.get("narration", ""))
        except (OSError, ValueError):
            topic = ""
    plain = re.sub(r"[\u064B-\u065F\u0670]", "", topic)
    tense = channel == "horror" or any(w in plain for w in ("حرب", "معركة", "كارثة", "اختفاء", "لغز"))
    space = channel == "science" and any(w in plain for w in ("فضاء", "كون", "كوكب", "نجوم"))
    mood = "tension" if tense else "space" if space else "discovery" if channel == "science" else "documentary"
    seed = int(hashlib.sha256((channel + topic).encode()).hexdigest()[:8], 16)
    root = (45 if tense else 52 if space else 57) + seed % 5
    chords = (0, 3, 5, 2) if tense else (0, 5, 7, 3)
    intervals = (0, 3, 7) if tense else (0, 4, 7)
    rate, length = 16000, 16
    score = mixed_audio.with_suffix(".score.wav")
    replacement = mixed_audio.with_suffix(".scored.mp3")
    samples = bytearray()
    for i in range(rate * length):
        t = i / rate
        phase = t % 4
        envelope = min(phase / 0.7, 1.0, (4 - phase) / 0.7)
        chord = chords[int(t / 4) % len(chords)]
        value = sum(math.sin(2 * math.pi * (440 * 2 ** ((root + chord + n - 69) / 12)) * t)
                    for n in intervals) / 3
        # A soft upper pulse adds motion without percussion masking consonants.
        pulse = (0.5 - 0.5 * math.cos(2 * math.pi * t / (1 if tense else 2)))
        value = 0.32 * envelope * value + 0.045 * pulse * math.sin(
            2 * math.pi * (440 * 2 ** ((root + 19 - 69) / 12)) * t)
        # Close the loop quietly to avoid clicks when the score repeats.
        edge = min(t / 0.1, (length - t) / 0.1, 1)
        samples.extend(struct.pack("<h", int(value * edge * 32767)))
    try:
        with wave.open(str(score), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(rate)
            audio.writeframes(samples)
        fade_start = max(0, duration - 2)
        filters = (
            "[0:a]aresample=48000[existing];"
            "[1:a]aresample=48000[control];"
            f"[2:a]aresample=48000,volume=0.14,afade=t=in:d=1.5,"
            f"afade=t=out:st={fade_start:.3f}:d=2[music];"
            "[music][control]sidechaincompress=threshold=0.015:ratio=10:"
            "attack=15:release=500:makeup=1[quiet];"
            "[existing][quiet]amix=inputs=2:duration=first:normalize=0,"
            "alimiter=limit=0.95:level=disabled[a]"
        )
        subprocess.run([media_executable("ffmpeg"), "-y", "-v", "error",
                        "-i", str(mixed_audio), "-i", str(narration),
                        "-stream_loop", "-1", "-i", str(score),
                        "-filter_complex", filters, "-map", "[a]",
                        "-t", f"{duration:.3f}", "-c:a", "libmp3lame",
                        "-b:a", "192k", str(replacement)], check=True, timeout=120)
        replacement.replace(mixed_audio)
        print(f"Background score: {channel}/{mood}; original synthesis; narration ducking enabled")
    finally:
        score.unlink(missing_ok=True)
        replacement.unlink(missing_ok=True)
