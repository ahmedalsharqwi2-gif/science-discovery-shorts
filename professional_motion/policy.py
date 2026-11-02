"""Permanent owner-confirmed duration policy; never pad or speed-change narration."""
from .duration_rules import require_duration as _require
PROFILE="science"
MIN_SECONDS=90.0
MAX_SECONDS=180.0
MIN_WORDS=260
MAX_WORDS=330
def require_duration(seconds):
    return _require(seconds,PROFILE)
