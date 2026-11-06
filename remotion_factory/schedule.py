"""Permanent Cairo civil-time policy for noon publication."""
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CAIRO = ZoneInfo("Africa/Cairo")
UTC = timezone.utc
POLICY = Path(__file__).resolve().parents[1] / "config" / "remotion_daily_release.json"


def _day(value):
    if isinstance(value, datetime):
        return value.astimezone(CAIRO).date()
    return date.fromisoformat(value) if isinstance(value, str) else value


def _config():
    return json.loads(POLICY.read_text(encoding="utf-8"))


def trial(day=None):
    """Compatibility API: noon mode is permanent, never finite or expiring."""
    return True


def hours(day=None):
    """Return permanent production/publication civil hours in Cairo."""
    cfg = _config()
    return int(cfg["production_local_hour"]), int(cfg["publication_local_hour"])


def production_day(day):
    """Production is always on the previous Cairo-local calendar day."""
    return _day(day) + timedelta(days=-1)


def _cairo_at(local_day, hour):
    return datetime.combine(_day(local_day), time(hour=hour), tzinfo=CAIRO)


def production_at(day):
    production_hour, _ = hours(day)
    return _cairo_at(production_day(day), production_hour)


def due_for(day):
    """Return the UTC instant corresponding to 12:00 Africa/Cairo."""
    _, publication_hour = hours(day)
    return _cairo_at(day, publication_hour).astimezone(UTC)


def clock_target(local):
    """Resolve an evening production run to the next Cairo-local publication date."""
    local = local.astimezone(CAIRO)
    if local.hour >= hours(local.date())[0]:
        return local.date() + timedelta(days=1)
    return None


def audit_day(local):
    """Evening production audits the following Cairo-local publication date."""
    local = local.astimezone(CAIRO)
    return local.date() + timedelta(days=1) if local.hour >= hours(local.date())[0] else local.date()


def checkpoints(day):
    """Return permanent noon checkpoints in Cairo civil time."""
    return ((9, 30), (11, 15), (12, 30), (21, 30))


def automatic_expected(day):
    return True
