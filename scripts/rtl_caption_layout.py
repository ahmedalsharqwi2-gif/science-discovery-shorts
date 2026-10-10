"""Stable right-to-left word placement for ASS/libass captions.

libass can reorder Arabic runs unexpectedly when inline color overrides are
embedded in a multiword RTL line. Positioning each shaped Arabic word as its
own event avoids mixed-direction runs while preserving the logical source text.
"""
from __future__ import annotations

import math
import subprocess
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=16)
def _font(font_name: str, font_size: int):
    from PIL import ImageFont

    candidates: list[str] = []
    try:
        result = subprocess.run(
            ["fc-match", "-f", "%{file}", font_name],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        if result.stdout.strip():
            candidates.append(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    candidates.extend(
        [
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    )
    for path in candidates:
        if Path(path).is_file():
            try:
                return ImageFont.truetype(path, font_size)
            except OSError:
                continue
    return ImageFont.load_default()


def _width(font, word: str, font_size: int) -> float:
    try:
        return float(font.getlength(word, direction="rtl", language="ar"))
    except (TypeError, ValueError):
        try:
            return float(font.getlength(word))
        except (AttributeError, TypeError, ValueError):
            return max(font_size * 0.45, len(word) * font_size * 0.62)


def layout_word_centers(
    words: list[str],
    canvas_width: int,
    font_size: int = 58,
    *,
    font_name: str = "Noto Naskh Arabic",
    side_margin: int = 70,
    word_gap: int | None = None,
) -> tuple[list[int], int]:
    """Return x-centers in logical word order, first Arabic word at the right.

    Widths are measured with the same installed font used by the ASS style.
    The returned horizontal scale (percent) keeps long four-word lines inside
    the safe area without changing their order or introducing line wraps.
    """
    if not words:
        return [], 100
    gap = word_gap if word_gap is not None else max(16, round(font_size * 0.38))
    font = _font(font_name, int(font_size))
    # ASS bold and outline add a little width beyond the regular-font metric.
    widths = [max(font_size * 0.42, _width(font, word, font_size) * 1.08) for word in words]
    raw_total = sum(widths) + gap * max(0, len(words) - 1)
    available = max(1, canvas_width - 2 * side_margin)
    scale = min(100, max(40, math.floor(available * 100 / max(1.0, raw_total))))
    factor = scale / 100.0
    scaled_widths = [width * factor for width in widths]
    scaled_gap = gap * factor
    right_edge = canvas_width / 2 + (sum(scaled_widths) + scaled_gap * max(0, len(words) - 1)) / 2
    centers: list[int] = []
    for width in scaled_widths:
        centers.append(round(right_edge - width / 2))
        right_edge -= width + scaled_gap
    return centers, scale
