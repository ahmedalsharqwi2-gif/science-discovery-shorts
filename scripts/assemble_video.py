"""Build a publishable vertical MP4 with Arabic captions timed to the real audio."""
from __future__ import annotations

import difflib
import logging
import os
import re
import subprocess
from pathlib import Path
from scripts.media_audio import add_topic_soundtrack

from scripts.pexels_video import build_pexels_track
from scripts.media_audio import ducking_filters

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
MAX_FULL_VIDEO_SECONDS = 180.0
FPS = 30
# Four words keeps captions readable while each word can be highlighted against
# its own spoken timestamp without changing the visible line.
WORDS_PER_CAPTION_CHUNK = 4
FONT_SIZE = 58
# 9:16 render; keep captions below phone camera notches and platform chrome.
CAPTION_TOP_SAFE_MARGIN = 260
log = logging.getLogger(__name__)
ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED\u08D3-\u08FF]")
BIDI_CONTROLS = re.compile(r"[\u061C\u200E\u200F\u202A-\u202E\u2066-\u2069]")
PUNCTUATION = str.maketrans(".,،؛:!?؟…-—_()[]{}\"«»/\\", " " * 23)


def probe_duration(audio_path: Path) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)], capture_output=True, text=True, check=True)
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise ValueError("Audio duration must be positive")
    return duration


def _ass_time(seconds: float) -> str:
    centiseconds = max(0, int(round(seconds * 100)))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, cs = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _ass_escape(text: str) -> str:
    # Keep ASS control sequences such as \N intact; escaping them as literal
    # backslashes prevents the intended line break from rendering.
    text = re.sub(r"\\(?!N)", r"\\\\", text)
    return text.replace("{", r"\{").replace("}", r"\}")


def _display_word(word: str) -> str:
    # ASS/libass performs Arabic shaping itself. Bidi control marks are
    # presentation metadata, not part of a word; leaving them in the event
    # payload can split a shaping run in some renderers.
    word = BIDI_CONTROLS.sub("", word)
    return ARABIC_DIACRITICS.sub("", word).translate(PUNCTUATION).strip()


def _caption_words(words: list[str]) -> list[str]:
    return [word for raw in words for word in [_display_word(raw)] if word]

def _caption_text(words: list[str], active_index: int | None = None) -> str:
    clean = _caption_words(words)
    if active_index is not None and clean:
        active_index = min(max(active_index, 0), len(clean) - 1)
    rendered = []
    for index, word in enumerate(clean):
        if active_index is not None and index == active_index:
            rendered.append(r"{\c&H000000FF&}" + word + r"{\c&H00FFFFFF&}")
        else:
            rendered.append(word)
    return " ".join(rendered)


def _rtl_ass_line(text: str) -> str:
    """Keep one bidi paragraph for Arabic; never place direction marks between words."""
    return text

def _norm(word: str) -> str:
    return _display_word(word).lower()


def _script_words(text: str) -> list[str]:
    return [w for w in re.findall(r"\S+", text) if _display_word(w)]


def align_words_with_whisper(audio_path: Path, script_words: list[str]) -> list[dict]:
    """Return monotonically increasing timestamps from the final audio."""
    from faster_whisper import WhisperModel
    model = WhisperModel(os.getenv("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    result = model.transcribe(
        str(audio_path),
        language="ar",
        word_timestamps=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 350},
        condition_on_previous_text=False,
    )
    segments = result[0] if isinstance(result, (tuple, list)) else result
    heard: list[tuple[str, float, float]] = []
    for segment in segments:
        for word in (getattr(segment, "words", None) or []):
            text = (getattr(word, "word", "") or "").strip()
            if text and word.start is not None and word.end is not None:
                heard.append((text, max(0.0, float(word.start)), max(0.0, float(word.end))))
    if not heard:
        raise RuntimeError("Whisper did not return Arabic word timestamps")
    expected = [_norm(w) for w in script_words]
    actual = [_norm(w) for w, _, _ in heard]
    matcher = difflib.SequenceMatcher(None, expected, actual, autojunk=False)
    timings: list[dict | None] = [None] * len(script_words)
    for block in matcher.get_matching_blocks():
        for offset in range(block.size):
            si, ai = block.a + offset, block.b + offset
            timings[si] = {"text": script_words[si], "offset": heard[ai][1], "duration": max(heard[ai][2] - heard[ai][1], 0.06)}
    known = [i for i, item in enumerate(timings) if item is not None]
    # A low match rate produces synthetic timings between unrelated words and
    # is perceived as stuttering captions. Use uniform timing instead unless
    # Whisper recognizes at least three quarters of the narration.
    if len(known) < max(1, int(len(script_words) * 0.75)):
        raise RuntimeError(f"Whisper alignment too weak: {len(known)}/{len(script_words)} words")
    for i, item in enumerate(timings):
        if item is not None:
            continue
        prev_i = max((j for j in known if j < i), default=None)
        next_i = min((j for j in known if j > i), default=None)
        if prev_i is None:
            next_item = timings[next_i]
            step = max(next_item["offset"] / (next_i + 1), 0.08)
            start, duration = step * i, max(step * 0.85, 0.06)
        elif next_i is None:
            prev_item = timings[prev_i]
            step = max(prev_item["duration"], 0.08)
            start, duration = prev_item["offset"] + step * (i - prev_i), step * 0.85
        else:
            prev_item, next_item = timings[prev_i], timings[next_i]
            left = prev_item["offset"] + prev_item["duration"]
            gap = max(next_item["offset"] - left, 0.08)
            slot = gap / (next_i - prev_i)
            start, duration = left + slot * (i - prev_i - 1), max(slot * 0.85, 0.06)
        timings[i] = {"text": script_words[i], "offset": start, "duration": duration}
    output = [item for item in timings if item is not None]
    previous_end = 0.0
    for item in output:
        item["offset"] = max(float(item["offset"]), previous_end)
        item["duration"] = max(float(item["duration"]), 0.06)
        previous_end = item["offset"] + item["duration"]
    return output


def _ass_header() -> str:
    return ("[Script Info]\nScriptType: v4.00+\n" f"PlayResX: {VIDEO_WIDTH}\nPlayResY: {VIDEO_HEIGHT}\n" "WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n" "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n" f"Style: Caption,Noto Naskh Arabic,{FONT_SIZE},&H00FFFFFF,&H00FFFFFF,&H0010182B,&HAA000000,1,0,0,0,100,100,0,0,1,3,1,8,70,70,{CAPTION_TOP_SAFE_MARGIN},1\n\n" "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")


def write_ass_subtitles(text: str, duration: float, ass_path: Path, audio_path: Path | None = None) -> None:
    words = _script_words(text)
    if not words:
        raise ValueError("Narration contains no words for subtitles")
    if audio_path is not None:
        try:
            events = align_words_with_whisper(audio_path, words)
        except Exception as exc:
            log.warning("Whisper alignment unavailable (%s); using weighted subtitle timing", exc)
            weights = [max(1, len(_norm(word))) for word in words]
            total_weight = sum(weights) or 1
            cursor = 0.0
            events = []
            for word, weight in zip(words, weights):
                word_duration = duration * weight / total_weight
                events.append({"text": word, "offset": cursor, "duration": word_duration})
                cursor += word_duration
    else:
        weights = [max(1, len(_norm(word))) for word in words]
        total_weight = sum(weights) or 1
        cursor = 0.0
        events = []
        for word, weight in zip(words, weights):
            word_duration = duration * weight / total_weight
            events.append({"text": word, "offset": cursor, "duration": word_duration})
            cursor += word_duration
    lines = [_ass_header()]
    for index in range(0, len(events), WORDS_PER_CAPTION_CHUNK):
        group = events[index:index + WORDS_PER_CAPTION_CHUNK]
        start = max(0.0, group[0]["offset"])
        end = min(duration, group[-1]["offset"] + group[-1]["duration"])
        if end <= start:
            end = min(duration, start + 0.25)
        words = [e["text"] for e in group]
        # Keep the complete four-word line stable, but replace only the
        # highlighted color at each real word boundary. There is no fade and
        # no gap, so the line cannot flash or appear to advance too quickly.
        for active_index, event in enumerate(group):
            word_start = max(start, float(event["offset"]))
            word_end = min(end, float(event["offset"]) + float(event["duration"]))
            if word_end <= word_start:
                word_end = min(end, word_start + 0.04)
            lines.append(
                f"Dialogue: 0,{_ass_time(word_start)},{_ass_time(max(word_end, word_start + 0.04))},Caption,,0,0,0,,"
                f"{_rtl_ass_line(_caption_text(words, active_index))}"
            )
    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _mix_science_audio(voice_path: Path, duration: float, output_path: Path, source_video: Path | None = None, topic: str = "") -> Path:
    """Keep narration clear and mix only scene-reviewed embedded sound."""
    inputs = ["-i", str(voice_path)]
    if source_video is not None:
        inputs += ["-i", str(source_video)]
        filters = ducking_filters("[0:a]", "[1:a]")
        filters.append("[voice][ducked]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95:level=disabled[a]")
    else:
        filters = ["[0:a]aresample=48000,alimiter=limit=0.95:level=disabled[a]"]
    subprocess.run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[a]",
                    "-t", f"{duration:.3f}", "-c:a", "libmp3lame", "-b:a", "192k", str(output_path)], check=True)
    add_topic_soundtrack(output_path, voice_path, duration, "science", topic)
    return output_path


def assemble_video(audio_path: Path, narration: str, output_path: Path, topic: str = "") -> Path:
    from scripts.cinematic_production import enabled, build
    if enabled():
        duration = probe_duration(audio_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        ass_path = output_path.with_suffix(".cinematic.ass")
        write_ass_subtitles(narration, duration, ass_path, audio_path=audio_path)
        build(audio_path, narration, output_path, {"title": topic, "narration": narration}, ass_path)
        return output_path
    duration = probe_duration(audio_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ass_path = output_path.with_suffix(".ass")
    write_ass_subtitles(narration, duration, ass_path, audio_path=audio_path)
    subtitles = _filter_path(ass_path)
    pexels_track = output_path.with_suffix(".pexels.mp4")
    mixed_audio = output_path.with_suffix(".mixed.mp3")
    has_pexels = build_pexels_track(os.getenv("PEXELS_API_KEY", "").strip(), topic, duration, pexels_track)
    if not has_pexels:
        ass_path.unlink(missing_ok=True)
        raise RuntimeError("لم تتوفر مقاطع Pexels كافية ومرتبطة بالموضوع؛ أوقفنا النشر.")
    try:
        _mix_science_audio(audio_path, duration, mixed_audio, pexels_track, topic=topic)
        subprocess.run(["ffmpeg", "-y", "-i", str(pexels_track), "-i", str(mixed_audio), "-filter_complex", f"[0:v]subtitles='{subtitles}':fontsdir='/usr/share/fonts/truetype/dejavu'[v]", "-map", "[v]", "-map", "1:a:0", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(output_path)], check=True)
    finally:
        ass_path.unlink(missing_ok=True)
        pexels_track.unlink(missing_ok=True)
        mixed_audio.unlink(missing_ok=True)
    return output_path
