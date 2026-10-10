#!/usr/bin/env python3
"""Pre-publish B-roll and montage quality gate.

The module is deliberately dependency-light so it can run in all three
repositories on GitHub Actions. It validates the rendered video and the
source-clip manifest before Buffer is called, and writes an auditable JSON
report to state/montage_quality.json.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

BLACK_RE = re.compile(r"black_start:([0-9.]+).*black_end:([0-9.]+)")


def _run(command: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def probe_video(path: Path) -> dict[str, Any]:
    code, out, err = _run([
        "ffprobe", "-v", "error", "-show_entries",
        "stream=width,height:format=duration", "-of", "json", str(path),
    ])
    if code or not out:
        raise RuntimeError(f"ffprobe failed for {path}: {err[:300]}")
    payload = json.loads(out)
    stream = (payload.get("streams") or [{}])[0]
    duration = float((payload.get("format") or {}).get("duration") or 0)
    return {
        "width": int(stream.get("width") or 0),
        "height": int(stream.get("height") or 0),
        "duration_seconds": round(duration, 3),
    }


def detect_black_intervals(path: Path) -> list[dict[str, float]]:
    code, _, err = _run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(path),
        "-vf", "blackdetect=d=0.30:pic_th=0.98", "-an", "-f", "null", "-",
    ])
    if code:
        raise RuntimeError(f"blackdetect failed for {path}: {err[-300:]}")
    intervals = []
    for match in BLACK_RE.finditer(err):
        start, end = float(match.group(1)), float(match.group(2))
        if end - start >= 0.30:
            intervals.append({"start": start, "end": end, "duration": round(end - start, 3)})
    return intervals


def load_manifest(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    if not path.exists():
        return [], [f"manifest missing: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"manifest unreadable: {exc}"]
    if not isinstance(data, list):
        return [], ["manifest must be a JSON list"]
    return [item for item in data if isinstance(item, dict)], []


def _approved_external_asset(item: dict[str, Any]) -> bool:
    source = str(item.get("source", "")).lower()
    source_url = str(item.get("source_url", ""))
    host = urlparse(source_url).hostname or ""
    license_name = str(item.get("license", "")).strip().lower()
    if source.startswith("pexels"):
        return license_name == "pexels" and host.endswith("pexels.com") and source_url.startswith("https://")
    if source.startswith("wikimedia_commons"):
        return license_name in {"public domain", "cc0"} and host == "commons.wikimedia.org" and source_url.startswith("https://")
    return False


def evaluate(
    video: Path,
    manifest: Path | None,
    clips_dir: Path | None,
    report_path: Path,
    expected: str,
    min_clips: int,
    max_black_seconds: float,
    min_external_sources: int = 0,
    min_external_share: float = 0.0,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if not video.is_file() or video.stat().st_size <= 0:
        errors.append(f"final video missing or empty: {video}")
        report = {"passed": False, "errors": errors, "warnings": warnings}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report

    media = probe_video(video)
    width, height, duration = media["width"], media["height"], media["duration_seconds"]
    if not width or not height or duration <= 0:
        errors.append("video has no valid stream dimensions or duration")
    ratio = width / height if height else 0
    if expected == "vertical" and not (0.50 <= ratio <= 0.65):
        errors.append(f"expected vertical video, got {width}x{height}")
    if expected == "landscape" and not (ratio >= 1.45):
        errors.append(f"expected landscape video, got {width}x{height}")

    manifest_items: list[dict[str, Any]] = []
    external_items: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    media_type_counts: dict[str, int] = {}
    if manifest:
        manifest_items, manifest_errors = load_manifest(manifest)
        errors.extend(manifest_errors)
        if len(manifest_items) < min_clips:
            errors.append(f"only {len(manifest_items)} B-roll entries; minimum is {min_clips}")
        ids = [str(item.get("pexels_id") or item.get("id") or item.get("file") or "") for item in manifest_items]
        ids = [item for item in ids if item]
        if len(ids) != len(set(ids)):
            warnings.append("duplicate B-roll source detected")
        if manifest_items:
            missing = []
            for item in manifest_items:
                source_name = str(item.get("source", "unknown"))
                media_type = str(item.get("media_type", "unknown"))
                source_counts[source_name] = source_counts.get(source_name, 0) + 1
                media_type_counts[media_type] = media_type_counts.get(media_type, 0) + 1
                if _approved_external_asset(item):
                    external_items.append(item)
                raw = str(item.get("file") or "")
                candidate = Path(raw)
                if not candidate.is_absolute():
                    candidate = Path.cwd() / candidate
                if not candidate.is_file() or candidate.stat().st_size <= 0:
                    missing.append(raw)
            if missing:
                errors.append(f"{len(missing)} manifest clips are missing on disk")
        external_ids = {
            str(item.get("asset_id") or item.get("pexels_id") or item.get("source_url"))
            for item in external_items
        }
        external_ids.discard("")
        external_share = len(external_items) / len(manifest_items) if manifest_items else 0.0
        if min_external_sources > 0 and len(external_ids) < min_external_sources:
            errors.append(f"only {len(external_ids)} unique licensed external media assets; minimum is {min_external_sources}")
        if min_external_share > 0 and external_share + 1e-9 < min_external_share:
            errors.append(f"only {len(external_items)}/{len(manifest_items)} scenes use licensed external media ({external_share:.0%}); minimum is {min_external_share:.0%}")
    elif clips_dir:
        clip_files = sorted(clips_dir.glob("*.mp4")) if clips_dir.exists() else []
        if len(clip_files) < min_clips:
            errors.append(f"only {len(clip_files)} prepared B-roll clips; minimum is {min_clips}")
        manifest_items = [{"file": str(item), "id": item.stem} for item in clip_files]

    black_intervals = detect_black_intervals(video)
    black_seconds = round(sum(item["duration"] for item in black_intervals), 3)
    if black_seconds > max_black_seconds:
        errors.append(f"black-frame coverage is {black_seconds:.2f}s; maximum is {max_black_seconds:.2f}s")

    unique_sources = len({str(item.get("pexels_id") or item.get("id") or item.get("file")) for item in manifest_items})
    clip_count = len(manifest_items)
    report = {
        "passed": not errors,
        "video": str(video),
        "media": media,
        "broll": {
            "clip_count": clip_count,
            "unique_sources": unique_sources,
            "coverage_estimate": 1.0 if clip_count else 0.0,
            "external_media_count": len(external_items),
            "external_unique_sources": len(external_ids) if manifest else 0,
            "external_scene_share": round(external_share, 3) if manifest else 0.0,
            "source_counts": source_counts,
            "media_type_counts": media_type_counts,
            "selection_policy": "footage-first licensed Pexels/Wikimedia assets, unique-source preference, minimum external-media coverage, rendered-video validation",
        },
        "black_intervals": black_intervals,
        "black_seconds": black_seconds,
        "errors": errors,
        "warnings": warnings,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate B-roll and montage before publishing")
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--clips-dir", type=Path)
    parser.add_argument("--report", type=Path, default=Path("state/montage_quality.json"))
    parser.add_argument("--expected", choices=("vertical", "landscape", "any"), default="any")
    parser.add_argument("--min-clips", type=int, default=4)
    parser.add_argument("--max-black-seconds", type=float, default=0.30)
    parser.add_argument("--min-external-sources", type=int, default=0)
    parser.add_argument("--min-external-share", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate(args.video, args.manifest, args.clips_dir, args.report, args.expected, args.min_clips, args.max_black_seconds,
                      args.min_external_sources, args.min_external_share)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report["passed"]:
        print("B-roll/montage quality gate failed; publishing is blocked.", file=sys.stderr)
        return 1
    print("B-roll/montage quality gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
