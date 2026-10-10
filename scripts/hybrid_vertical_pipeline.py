#!/usr/bin/env python3
"""Hybrid vertical documentary renderer: storyboard + segmented Arabic TTS.

Storyboard example:
{
  "music": "assets/music/history_stone_echoes.mp3",
  "voice": "ar-SA-HamedNeural",
  "rate": "-4%",
  "pitch": "-2Hz",
  "scenes": [
    {"id": "hook", "image": "assets/scene_001.jpg",
     "text": "حضارة عظيمة... لكن أين اختفت؟", "motion": "zoom_in"},
    {"id": "evidence", "image": "assets/scene_002.jpg",
     "text": "كانت تبني مدنًا تلامس السماء.", "motion": "pan_right"}
  ]
}

Paths in storyboard JSON are resolved relative to the storyboard file first,
then relative to the current working directory. Music is per repository: the
storyboard's music path (or --music) must point inside that repository's own
assets/music folder when used in CI. If no music is supplied, a local FFmpeg
ambient bed is generated as a fallback.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

try:
    import edge_tts
except ImportError as exc:  # pragma: no cover
    raise SystemExit("edge-tts is required: python -m pip install edge-tts") from exc

WIDTH = 1080
HEIGHT = 1920
FPS = 30
FONT_NAME = "Noto Sans Arabic"
DEFAULT_VOICE = "ar-SA-HamedNeural"
DEFAULT_RATE = "-10%"
DEFAULT_PITCH = "-2Hz"


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(
            "Command failed:\n" + " ".join(command) + "\n\n" + result.stderr[-5000:]
        )
    return result


def probe_duration(path: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    value = float(result.stdout.strip())
    if value <= 0:
        raise ValueError(f"Invalid duration for {path}")
    return value


def resolve_path(value: str | Path, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    candidates = []
    if base is not None:
        candidates.append(base / path)
    candidates.append(Path.cwd() / path)
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else path.resolve()


async def synthesize_voice(text: str, output: Path, voice: str, rate: str, pitch: str) -> None:
    spoken = re.sub(r"\s+", " ", text).strip()
    if not spoken:
        raise ValueError("Scene narration is empty")
    await edge_tts.Communicate(spoken, voice=voice, rate=rate, pitch=pitch).save(str(output))


def ass_time(seconds: float) -> str:
    total_cs = max(0, int(round(seconds * 100)))
    hours, rem = divmod(total_cs, 360000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}")


def caption_text(text: str, max_words: int = 7) -> str:
    words = ass_escape(text).split()
    if len(words) <= max_words:
        return " ".join(words)
    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + r"\N" + " ".join(words[midpoint:])


def write_ass(events: list[dict[str, Any]], output: Path) -> None:
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {WIDTH}",
        f"PlayResY: {HEIGHT}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Caption,{FONT_NAME},58,&H00F4F1EA,&H00F4F1EA,&H0010182B,&HAA000000,1,0,0,0,100,100,0,0,1,4,2,8,70,70,300,1",
        "", "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for event in events:
        # Strip bidi controls from display only; libass handles Arabic shaping and RTL.
        text = re.sub(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", event["text"])
        tokens = text.split()
        highlight_keys = {normalize_match_word(word) for word in event.get("highlight_words", [])[:2]}
        styled = []
        for token in tokens:
            safe = ass_escape(token)
            if normalize_match_word(token) in highlight_keys:
                safe = r"{\c&H000000FF&}" + safe + r"{\c}"
            styled.append(safe)
        if len(styled) > 7:
            midpoint = (len(styled) + 1) // 2
            rendered = " ".join(styled[:midpoint]) + r"\N" + " ".join(styled[midpoint:])
        else:
            rendered = " ".join(styled)
        lines.append(f"Dialogue: 0,{ass_time(event['start'])},{ass_time(event['end'])},Caption,,0,0,0,,{{\\fad(120,150)}}{rendered}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")



_BIDI_CONTROLS = dict.fromkeys(map(ord, "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069"), None)
_DIACRITICS = re.compile(r"[\u064b-\u065f\u0670\u06d6-\u06ed]")
_PUNCT = re.compile(r"[^\w\u0621-\u064a\u0660-\u0669\u06f0-\u06f9]+", re.UNICODE)
_WHISPER_MODEL = None

def normalize_match_word(word: str) -> str:
    """Internal-only Arabic normalization; never use this value for display."""
    value = unicodedata.normalize("NFKC", word).translate(_BIDI_CONTROLS).replace("ـ", "")
    alef_map = {ord("أ"): ord("ا"), ord("إ"): ord("ا"), ord("آ"): ord("ا"), ord("ٱ"): ord("ا"), ord("ى"): ord("ي")}
    value = _DIACRITICS.sub("", value).translate(alef_map)
    return _PUNCT.sub("", value).lower()

def _text_words(text: str) -> list[str]:
    return [w for w in re.sub(r"[\u061c\u200e\u200f\u202a-\u202e\u2066-\u2069]", "", text).split() if normalize_match_word(w)]

def _whisper_word_spans(audio: Path, text: str, duration: float) -> tuple[list[dict[str, Any]], str]:
    """Return spoken words with Whisper times, falling back without stopping the render."""
    global _WHISPER_MODEL
    display_words = _text_words(text)
    try:
        from faster_whisper import WhisperModel
        if _WHISPER_MODEL is None:
            model_name = os.getenv("CAPTION_WHISPER_MODEL", "small")
            _WHISPER_MODEL = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = _WHISPER_MODEL.transcribe(
            str(audio), language="ar", word_timestamps=True, vad_filter=True,
            condition_on_previous_text=False,
        )
        recognized: list[dict[str, Any]] = []
        for segment in segments:
            for word in (segment.words or []):
                if word.start is not None and word.end is not None:
                    recognized.append({"key": normalize_match_word(word.word),
                                       "start": max(0.0, float(word.start)),
                                       "end": min(duration, float(word.end))})
        expected = [normalize_match_word(w) for w in display_words]
        # Only transfer times when normalized sequence matches completely. This avoids
        # silently dropping or substituting text when ASR mishears a word.
        if recognized and [w["key"] for w in recognized] == expected:
            return ([{"text": word, "start": rec["start"], "end": max(rec["start"] + 0.01, rec["end"])}
                     for word, rec in zip(display_words, recognized)], "whisper")
    except Exception as exc:
        print(f"WARNING: Whisper word alignment unavailable; using estimated timing: {exc}", file=sys.stderr)
    # Stable character-weighted fallback; avoids the inaccurate constant words/second rule.
    weights = [max(1, len(normalize_match_word(w))) for w in display_words]
    total = sum(weights) or 1
    spans, offset = [], 0.0
    for word, weight in zip(display_words, weights):
        end = offset + duration * weight / total
        spans.append({"text": word, "start": offset, "end": end})
        offset = end
    return spans, "estimated_fallback"

def _caption_chunks(word_spans: list[dict[str, Any]], max_words: int = 7,
                    max_chars: int = 38) -> list[dict[str, Any]]:
    """Group word spans into readable captions, preserving each original display token."""
    if max_words < 1:
        raise ValueError("max_words must be positive")
    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    def flush() -> None:
        nonlocal current
        if not current:
            return
        start, end = current[0]["start"], current[-1]["end"]
        # Keep a readable minimum duration where possible without overlapping the next event.
        if end - start < 0.45:
            end = start + 0.45
        text = " ".join(item["text"] for item in current)
        chunks.append({"start": start, "end": end, "text": text})
        current = []
    for item in word_spans:
        proposed = current + [item]
        joined = " ".join(part["text"] for part in proposed)
        punctuation_break = bool(current and re.search(r"[.!?؟،؛:]$", current[-1]["text"]))
        if current and (len(proposed) > max_words or len(joined) > max_chars or punctuation_break):
            flush()
        current.append(item)
    flush()
    # Do not leave a one-word tail if it can be combined under both visual bounds.
    if len(chunks) > 1 and len(chunks[-1]["text"].split()) == 1:
        a, b = chunks[-2], chunks[-1]
        merged = a["text"] + " " + b["text"]
        if len(merged) <= max_chars and len(merged.split()) <= max_words:
            chunks[-2:] = [{"start": a["start"], "end": b["end"], "text": merged}]
    return chunks

def validate_caption_events(events: list[dict[str, Any]], duration: float) -> None:
    previous_start = -1.0
    for event in events:
        if not event.get("text", "").strip():
            raise ValueError("Caption event has empty text")
        if event["start"] < 0 or event["end"] <= event["start"]:
            raise ValueError("Caption event has invalid timing")
        if event["start"] < previous_start:
            raise ValueError("Caption events are not ordered")
        if event["end"] > duration + 0.5:
            raise ValueError("Caption event extends beyond audio/video duration")
        if len(event["text"]) > 76:
            raise ValueError("Caption line exceeds the 38-character-per-line bound")
        previous_start = event["start"]

def make_local_ambient_music(output: Path, duration: float) -> None:
    graph = (
        "[0:a]volume=0.035,lowpass=f=900,tremolo=f=0.10:d=0.65,"
        "afade=t=in:st=0:d=2,afade=t=out:st="
        f"{max(0.0, duration - 2):.3f}:d=2[m1];"
        "[1:a]volume=0.018,lowpass=f=500,tremolo=f=0.10:d=0.55,"
        "afade=t=in:st=0:d=2,afade=t=out:st="
        f"{max(0.0, duration - 2):.3f}:d=2[m2];"
        "[m1][m2]amix=inputs=2:duration=longest:normalize=0[m]"
    )
    run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=110:sample_rate=48000",
        "-f", "lavfi", "-i", "sine=frequency=164.81:sample_rate=48000",
        "-t", f"{duration:.3f}", "-filter_complex", graph, "-map", "[m]",
        "-c:a", "libmp3lame", "-b:a", "96k", str(output),
    ])


def motion_filter(motion: str) -> str:
    motion = (motion or "zoom_in").lower()
    if motion == "zoom_out":
        zoom = "max(1.0,1.05-zoom+1.0-1.0)"  # replaced below for readability
        zoom = "max(1.0,1.05-on/1500)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        zoom = "min(zoom+0.0005,1.04)"
        x = "max(0,(iw-iw/zoom)*(1-on/1500))"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        zoom = "min(zoom+0.0005,1.04)"
        x = "min(iw-iw/zoom,(iw-iw/zoom)*(on/1500))"
        y = "ih/2-(ih/zoom/2)"
    else:
        zoom = "min(zoom+0.0009,1.05)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    return (
        "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s=1080x1920:fps=30,format=yuv420p"
    )


def render_scene_visual(image: Path, output: Path, duration: float, motion: str) -> None:
    run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(image), "-t", f"{duration:.3f}",
        "-vf", motion_filter(motion), "-an", "-c:v", "libx264", "-preset", "medium",
        "-crf", "20", "-pix_fmt", "yuv420p", str(output),
    ])


def concat_audio(paths: list[Path], output: Path) -> None:
    if len(paths) == 1:
        shutil.copy2(paths[0], output)
        return
    inputs: list[str] = []
    for path in paths:
        inputs += ["-i", str(path)]
    labels = "".join(f"[{i}:a]" for i in range(len(paths)))
    graph = f"{labels}concat=n={len(paths)}:v=0:a=1[a]"
    run(["ffmpeg", "-y", *inputs, "-filter_complex", graph, "-map", "[a]",
         "-c:a", "aac", "-b:a", "160k", str(output)])


def concat_video(paths: list[Path], output: Path) -> None:
    list_path = output.with_suffix(".concat.txt")
    list_path.write_text("\n".join(f"file '{p.resolve().as_posix()}'" for p in paths) + "\n", encoding="utf-8")
    try:
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path),
             "-c", "copy", "-movflags", "+faststart", str(output)])
    finally:
        list_path.unlink(missing_ok=True)


def mix_full_audio(voice: Path, music: Path, output: Path, duration: float, music_gain: float = 0.26) -> None:
    graph = (
        "[0:a]aresample=48000,volume=1.0,asplit=2[voice_main][sidechain];"
        f"[1:a]aresample=48000,volume={music_gain:.3f}[music];"
        "[music][sidechain]sidechaincompress=threshold=0.035:ratio=8:"
        "attack=20:release=500:makeup=1[ducked];"
        "[voice_main][ducked]amix=inputs=2:duration=first:dropout_transition=0,"
        "alimiter=limit=0.95:level=disabled[a]"
    )
    run(["ffmpeg", "-y", "-i", str(voice), "-stream_loop", "-1", "-i", str(music),
         "-filter_complex", graph, "-map", "[a]", "-t", f"{duration:.3f}",
         "-c:a", "aac", "-b:a", "160k", str(output)])


def load_storyboard(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ValueError("Storyboard must contain a non-empty scenes array")
    return data, data["scenes"]


def build_storyboard(storyboard_path: Path, output: Path, music_override: Path | None = None,
                     voice_override: str | None = None, rate_override: str | None = None,
                     pitch_override: str | None = None) -> dict[str, Any]:
    config, raw_scenes = load_storyboard(storyboard_path)
    base = storyboard_path.parent
    voice = voice_override or config.get("voice") or DEFAULT_VOICE
    rate = rate_override or config.get("rate") or DEFAULT_RATE
    pitch = pitch_override or config.get("pitch") or DEFAULT_PITCH
    music_value = music_override or (resolve_path(config["music"], base) if config.get("music") else None)
    if music_value is not None and not music_value.exists():
        raise FileNotFoundError(f"Repository music file not found: {music_value}")
    music_gain = float(config.get("music_gain", 0.26))
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="hybrid_storyboard_") as temp:
        work = Path(temp)
        voice_paths: list[Path] = []
        visual_paths: list[Path] = []
        caption_events: list[dict[str, Any]] = []
        cursor = 0.0
        metadata_scenes = []
        for index, raw in enumerate(raw_scenes, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"Scene {index} is not an object")
            text = str(raw.get("text") or raw.get("narration") or "").strip()
            image_value = raw.get("image") or raw.get("visual")
            if not text or not image_value:
                raise ValueError(f"Scene {index} needs image and text")
            image = resolve_path(str(image_value), base)
            if not image.exists():
                raise FileNotFoundError(f"Scene {index} image not found: {image}")
            voice_path = work / f"voice_{index:03d}.mp3"
            asyncio.run(synthesize_voice(text, voice_path, voice, rate, pitch))
            voice_duration = probe_duration(voice_path)
            scene_duration = voice_duration + float(raw.get("tail_seconds", 0.40))
            visual_path = work / f"visual_{index:03d}.mp4"
            render_scene_visual(image, visual_path, scene_duration, str(raw.get("motion", "zoom_in")))
            voice_paths.append(voice_path)
            visual_paths.append(visual_path)
            word_spans, alignment_method = _whisper_word_spans(voice_path, text, voice_duration)
            repo_profile = {"arabic-horror-stories": "horror", "documented-history-stories": "history"}.get(Path(__file__).resolve().parent.parent.name, "science")
            profile = str(raw.get("content_type") or config.get("content_type") or repo_profile).lower()
            max_words = 5 if profile in {"horror", "رعب"} else 6 if profile in {"history", "التاريخ"} else 7
            for caption in _caption_chunks(word_spans, max_words=max_words):
                caption_events.append({"start": cursor + caption["start"],
                                       "end": min(cursor + voice_duration, cursor + caption["end"]),
                                       "text": caption["text"],
                                       "highlight_words": list(raw.get("highlight_words", []))[:2]})
            metadata_scenes.append({
                "index": index, "id": raw.get("id", f"scene_{index:03d}"),
                "image": str(image), "motion": raw.get("motion", "zoom_in"),
                "voice_duration": round(voice_duration, 3),
                "scene_duration": round(scene_duration, 3),
                "caption_alignment": alignment_method,
            })
            cursor += scene_duration

        concatenated_video = work / "video_concat.mp4"
        concat_video(visual_paths, concatenated_video)
        concatenated_voice = work / "voice_concat.m4a"
        concat_audio(voice_paths, concatenated_voice)
        total_duration = probe_duration(concatenated_video)
        music_path = work / "music.mp3"
        if music_value is not None:
            shutil.copy2(music_value, music_path)
            music_label = str(music_value)
        else:
            make_local_ambient_music(music_path, total_duration)
            music_label = "local_ffmpeg_ambient"
        mixed_audio = work / "mixed.m4a"
        mix_full_audio(concatenated_voice, music_path, mixed_audio, total_duration, music_gain)
        ass_path = work / "captions.ass"
        validate_caption_events(caption_events, total_duration)
        write_ass(caption_events, ass_path)
        ass_filter = str(ass_path).replace("\\", "/").replace(":", r"\:")
        run(["ffmpeg", "-y", "-i", str(concatenated_video), "-i", str(mixed_audio),
             "-vf", f"subtitles='{ass_filter}'", "-map", "0:v:0", "-map", "1:a:0",
             "-t", f"{total_duration:.3f}", "-c:v", "libx264", "-preset", "medium",
             "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
             "-shortest", "-movflags", "+faststart", str(output)])
        return {
            "output": str(output), "mode": "storyboard", "voice": voice,
            "rate": rate, "pitch": pitch, "music": music_label,
            "scene_count": len(metadata_scenes), "duration": round(probe_duration(output), 3),
            "width": WIDTH, "height": HEIGHT, "scenes": metadata_scenes,
        }


def build_single(image: Path, text: str, output: Path, music: Path | None,
                 voice: str, rate: str, pitch: str) -> dict[str, Any]:
    storyboard = output.with_suffix(".storyboard.json")
    storyboard.write_text(json.dumps({"music": str(music) if music else None,
        "voice": voice, "rate": rate, "pitch": pitch,
        "scenes": [{"image": str(image), "text": text, "motion": "zoom_in"}]}, ensure_ascii=False), encoding="utf-8")
    try:
        return build_storyboard(storyboard, output, music_override=music)
    finally:
        storyboard.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storyboard", type=Path)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--text")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--voice", default=os.getenv("EDGE_TTS_VOICE", DEFAULT_VOICE))
    parser.add_argument("--rate", default=os.getenv("EDGE_TTS_RATE", DEFAULT_RATE))
    parser.add_argument("--pitch", default=os.getenv("EDGE_TTS_PITCH", DEFAULT_PITCH))
    parser.add_argument("--metadata", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.storyboard:
            metadata = build_storyboard(args.storyboard.resolve(), args.output, args.music,
                                       args.voice, args.rate, args.pitch)
        elif args.image and args.text:
            metadata = build_single(args.image, args.text, args.output, args.music,
                                    args.voice, args.rate, args.pitch)
        else:
            raise ValueError("Use --storyboard, or both --image and --text")
        if args.metadata:
            args.metadata.parent.mkdir(parents=True, exist_ok=True)
            args.metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(metadata, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
