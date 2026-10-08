"""Cycle stored repository music by production run number, with narration ducking."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path


def select_track(root: Path, channel: str) -> Path:
    directory = root / "assets" / "music"
    tracks = sorted(p for p in directory.glob("*") if p.suffix.lower() in {".wav", ".mp3"})
    if not tracks:
        raise FileNotFoundError(f"No background music tracks found in {directory}")
    requested = os.getenv("BACKGROUND_MUSIC_TRACK", "").strip()
    if requested:
        candidate = Path(requested)
        if not candidate.is_absolute():
            candidate = root / candidate
        if candidate not in tracks or not candidate.is_file():
            raise FileNotFoundError(f"Requested soundtrack is not available: {candidate}")
        return candidate
    raw = os.getenv("MUSIC_ROTATION_INDEX", os.getenv("GITHUB_RUN_ID", "0"))
    try:
        index = (int(raw) - (1 if "MUSIC_ROTATION_INDEX" in os.environ else 0)) % len(tracks)
    except ValueError:
        index = 0
    return tracks[index]


def mix_background_music(mixed_audio: Path, narration: Path, duration: float, root: Path, channel: str) -> Path:
    if os.getenv("BACKGROUND_MUSIC_ENABLED", "true").lower() != "true":
        return mixed_audio
    track = select_track(root, channel)
    volume = float(os.getenv("BACKGROUND_MUSIC_VOLUME", os.getenv("MUSIC_VOLUME", "0.12")))
    fade_start = max(0.0, duration - 2.0)
    replacement = mixed_audio.with_suffix(".music.mp3")
    filters = ("[0:a]aresample=48000[existing];[1:a]aresample=48000[voice];" f"[2:a]aresample=48000,volume={volume:.4f},afade=t=in:d=1.5,afade=t=out:st={fade_start:.3f}:d=2[music];" "[music][voice]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=450:makeup=1[quiet];" "[existing][quiet]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95:level=disabled[a]")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mixed_audio), "-i", str(narration), "-stream_loop", "-1", "-i", str(track), "-filter_complex", filters, "-map", "[a]", "-t", f"{duration:.3f}", "-c:a", "libmp3lame", "-b:a", "192k", str(replacement)], check=True, timeout=120)
    replacement.replace(mixed_audio)
    print(f"Background music: {channel}/{track.name} volume={volume:.3f} rotation={os.getenv('MUSIC_ROTATION_INDEX', os.getenv('GITHUB_RUN_ID', 'local'))}")
    return mixed_audio
