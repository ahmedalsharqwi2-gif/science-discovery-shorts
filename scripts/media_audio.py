"""Normalize clip audio layouts and duck scene audio beneath narration."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path


def has_audio(path: Path) -> bool:
    result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
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
