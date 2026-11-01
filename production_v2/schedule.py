"""Same-day Cairo scheduling with explicit late/early outcomes."""
from datetime import datetime, timezone
import math
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo('Africa/Cairo')


def window(now: datetime) -> dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('A timezone-aware current time is required')
    local = now.astimezone(CAIRO)
    due = local.replace(hour=17, minute=0, second=0, microsecond=0)
    start = local.replace(hour=9, minute=0, second=0, microsecond=0)
    cutoff = local.replace(hour=15, minute=0, second=0, microsecond=0)
    reason = 'too_early' if local < start else 'missed' if local >= cutoff else 'eligible'
    return {'reason': reason, 'run': reason == 'eligible',
            'slot': 'daily-' + local.date().isoformat(),
            'due_at': due.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')}


def require_duration(seconds: float) -> float:
    value = float(seconds)
    if not math.isfinite(value) or not 120 <= value < 180:
        raise ValueError('Daily films must be at least 120 and less than 180 seconds')
    return value


def require_future_due(due: str, now: datetime) -> datetime:
    value = datetime.fromisoformat(due.replace('Z', '+00:00'))
    if value.tzinfo is None or now.tzinfo is None:
        raise ValueError('Absolute timezone-aware due and current times required')
    if value <= now:
        raise ValueError('Publication slot missed; no immediate posting or silent rollover')
    local = value.astimezone(CAIRO)
    if (local.hour, local.minute, local.second, local.microsecond) != (17, 0, 0, 0):
        raise ValueError('Publication must target exactly 17:00 Cairo')
    if local.date() != now.astimezone(CAIRO).date():
        raise ValueError('Only the current Cairo civil day can be scheduled')
    return value
