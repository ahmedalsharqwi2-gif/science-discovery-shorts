"""Shared Arabic caption policy for vertical motion renders."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

TEXT_X = (190, 890)
TEXT_Y = (290, 1248)
TEXT_X_LOWER = (190, 780)
LOWER_BAND_Y = 840
MAX_WORDS = 4
MIN_DURATION = 0.9
MAX_LINES = 2

@dataclass(frozen=True)
class CaptionEvent:
    start: float
    end: float
    text: str


def _words(text: str) -> list[str]:
    return [w for w in text.replace("\n", " ").split() if w]


def validate_event(event: CaptionEvent, *, duration: float | None = None) -> CaptionEvent:
    if event.start < 0 or event.end <= event.start:
        raise ValueError("caption timing must be monotonic and positive")
    if duration is not None and event.end > duration + 1e-6:
        raise ValueError("caption exceeds audio duration")
    if len(_words(event.text)) > MAX_WORDS:
        raise ValueError("caption exceeds four-word readability budget")
    if event.end - event.start < MIN_DURATION:
        raise ValueError("caption event is shorter than 0.9 seconds; review alignment")
    if "\n" in event.text and len(event.text.splitlines()) > MAX_LINES:
        raise ValueError("caption exceeds two lines")
    return event


def assert_bbox_in_safe_zone(name: str, bbox: tuple[float, float, float, float], *, kind: str = "text") -> None:
    if kind not in {"text", "chrome"}:
        raise ValueError("kind must be text or chrome")
    x0, y0, x1, y1 = bbox
    if x0 < 0 or y0 < 0 or x1 > 1080 or y1 > 1920 or x1 <= x0 or y1 <= y0:
        raise ValueError(f"{name}: invalid bbox")
    if kind == "chrome":
        if y0 < 130:
            raise ValueError(f"{name}: chrome is above the permitted chrome band")
        return
    if x0 < TEXT_X[0] or x1 > TEXT_X[1] or y0 < TEXT_Y[0] or y1 > TEXT_Y[1]:
        raise ValueError(f"{name}: text leaves the shared safe zone")
    if y1 >= LOWER_BAND_Y and (x0 < TEXT_X_LOWER[0] or x1 > TEXT_X_LOWER[1]):
        raise ValueError(f"{name}: lower-band text enters the platform action rail")


def validate_caption_events(events: Iterable[CaptionEvent], *, duration: float | None = None) -> list[CaptionEvent]:
    checked = [validate_event(e, duration=duration) for e in events]
    for previous, current in zip(checked, checked[1:]):
        if current.start < previous.end:
            raise ValueError("caption events overlap")
    return checked
