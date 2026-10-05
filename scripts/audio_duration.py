"""Fit narration to the reel window without cutting words or changing pitch."""
import subprocess
from pathlib import Path

from scripts.assemble_video import probe_duration


def fit_narration(path: Path, minimum: float, maximum: float, target: float) -> float:
    duration = probe_duration(path)
    if minimum <= duration <= maximum:
        return duration
    target = min(maximum - 1, max(minimum + 1, target))
    tempo = duration / target
    if tempo > 1.25 and duration / (maximum - 0.25) <= 1.25:
        target = maximum - 0.25
        tempo = duration / target
    elif tempo < 0.85 and duration / (minimum + 0.25) >= 0.85:
        target = minimum + 0.25
        tempo = duration / target
    # Fail closed for material changes to speaking pace.
    if not 0.85 <= tempo <= 1.25:
        raise ValueError(f"Audio duration cannot fit naturally: {duration:.2f}s (tempo {tempo:.2f})")
    fitted = path.with_name(path.stem + ".fitted" + path.suffix)
    subprocess.run(["ffmpeg", "-y", "-i", str(path), "-filter:a", f"atempo={tempo:.8f}",
                    "-vn", str(fitted)], check=True, capture_output=True)
    actual = probe_duration(fitted)
    if not minimum <= actual <= maximum:
        fitted.unlink(missing_ok=True)
        raise ValueError(f"Fitted narration remains outside duration window: {actual:.2f}s")
    fitted.replace(path)
    return actual
