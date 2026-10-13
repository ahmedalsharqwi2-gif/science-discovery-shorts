"""Free Arabic narration with word-safe requests and decoded PCM assembly."""
from __future__ import annotations

import array
import re
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path


def narration_tokens(text: str) -> list[str]:
    """Keep punctuation/diacritics; never split a word at the 100-char limit."""
    words = re.sub(r"\s+", " ", text).strip().split()
    tokens = []
    while words:
        count, length = 0, 0
        for word in words:
            candidate = length + bool(count) + len(word)
            if candidate > 100:
                break
            count += 1
            length = candidate
        if count == 0:
            raise ValueError("A narration word exceeds the free TTS request limit")
        # Prefer a natural clause boundary, without treating hyphens in names
        # or decimal punctuation as separate utterances.
        boundaries = [i + 1 for i, w in enumerate(words[:count])
                      if w.endswith((".", "؟", "!", "،", "؛", "…"))]
        if boundaries:
            count = boundaries[-1]
        tokens.append(" ".join(words[:count]))
        words = words[count:]
    return tokens


def _ffmpeg() -> str:
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise FileNotFoundError("FFmpeg is required for narration assembly")
    return str(Path(executable).resolve())


def _decode(part: Path, target: Path) -> None:
    subprocess.run([_ffmpeg(), "-y", "-v", "error", "-i", str(part),
                    "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(target)],
                   check=True, timeout=120)


def _boundary_pcm(path: Path) -> bytes:
    """Remove only excess near-silent outer padding; keep 80 ms guards.

    No internal silence removal, overlap, crossfade, or spoken-sample trimming.
    A conservative peak threshold protects quiet consonants at joins.
    """
    with wave.open(str(path), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 24000):
            raise ValueError("Unexpected narration PCM format")
        data = source.readframes(source.getnframes())
    samples = array.array("h", data)
    window, guard = 240, 1920
    left, right = 0, len(samples)
    while left + window < right and max(abs(v) for v in samples[left:left + window]) <= 32:
        left += window
    while right - window > left and max(abs(v) for v in samples[right - window:right]) <= 32:
        right -= window
    if left >= right or not any(abs(v) > 32 for v in samples[left:right]):
        raise RuntimeError("Free Arabic TTS returned silent audio")
    return samples[max(0, left - guard):min(len(samples), right + guard)].tobytes()


def google_arabic_voice(text: str, output: Path, *, slow: bool = False) -> None:
    if not text.strip():
        raise ValueError("Cannot synthesize empty narration")
    from gtts import gTTS
    tokens = narration_tokens(text)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.stem + ".building.mp3")
    try:
        with tempfile.TemporaryDirectory(prefix="arabic-voice-", dir=output.parent) as directory:
            work = Path(directory)
            pcm_path = work / "joined.wav"
            # Each response is an independent MP3 stream. Decode separately so
            # embedded headers/encoder delay cannot create gaps in concatenation.
            with wave.open(str(pcm_path), "wb") as joined:
                joined.setnchannels(1)
                joined.setsampwidth(2)
                joined.setframerate(24000)
                for token in tokens:
                    part, decoded = work / "part.mp3", work / "part.wav"
                    gTTS(text=token, lang="ar", lang_check=False, slow=slow,
                         pre_processor_funcs=[], tokenizer_func=narration_tokens,
                         timeout=(10, 30)).save(str(part))
                    _decode(part, decoded)
                    joined.writeframes(_boundary_pcm(decoded))
            subprocess.run([_ffmpeg(), "-y", "-v", "error", "-i", str(pcm_path),
                            "-c:a", "libmp3lame", "-b:a", "192k", str(temporary)],
                           check=True, timeout=120)
            if not temporary.exists() or temporary.stat().st_size == 0:
                raise RuntimeError("Free Arabic TTS returned no audio")
            temporary.replace(output)
            print(f"Free Arabic TTS: {len(tokens)} word-safe requests, PCM joins, no added pauses")
    finally:
        temporary.unlink(missing_ok=True)
