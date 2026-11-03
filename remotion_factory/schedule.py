"""Cairo civil-time policy for the owner-approved two-week noon experiment."""
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
CAIRO = ZoneInfo('Africa/Cairo')
POLICY = Path(__file__).resolve().parents[1] / 'config/remotion_daily_release.json'

def trial(day):
    """Return whether a publication date belongs to the approved experiment."""
    day = date.fromisoformat(day) if isinstance(day,str) else day
    cfg = json.loads(POLICY.read_text()).get('publication_time_trial',{})
    return bool(cfg.get('enabled') and cfg['start_date'] <= day.isoformat() < cfg['end_date_exclusive'])

def hours(day):
    """Return preparation and publication civil hours for a release date."""
    cfg = json.loads(POLICY.read_text())
    item = cfg['publication_time_trial'] if trial(day) else cfg
    return item['production_local_hour'],item['publication_local_hour']

def production_day(day):
    """Production precedes the release by a day only within the trial."""
    day = date.fromisoformat(day) if isinstance(day,str) else day
    return day - timedelta(days=1) if trial(day) else day

def production_at(day):
    """Resolve the actual preparation instant using the Cairo timezone."""
    return datetime.combine(production_day(day),time(hours(day)[0]),CAIRO)

def due_for(day):
    """Resolve publication with the date-specific daylight-saving offset."""
    day = date.fromisoformat(day) if isinstance(day,str) else day
    return datetime.combine(day,time(hours(day)[1]),CAIRO).astimezone(timezone.utc)

def clock_target(local):
    """Map an observed clock date to its intended immutable publication date."""
    tomorrow = local.date()+timedelta(days=1)
    if trial(tomorrow) and (trial(local.date()) or local.hour>=19):return tomorrow
    if trial(local.date()):return None
    return local.date()

def audit_day(local):
    """Evening reports assess tomorrow after preparation starts."""
    tomorrow=local.date()+timedelta(days=1)
    return tomorrow if local.hour>=19 and trial(tomorrow) else local.date()

def checkpoints(day):
    """Return audit civil times applicable to the clock date."""
    points = [(9,30),(11,15),(12,30)] if trial(day) else [(11,30),(15,0),(16,15),(17,30)]
    if trial(day+timedelta(days=1)):points.append((21,30))
    return tuple(points)

def automatic_expected(day):
    """The transition inventory is not retroactively called an automatic evening run."""
    cfg=json.loads(POLICY.read_text()).get('publication_time_trial',{})
    return not trial(day) or day.isoformat() >= cfg['first_automatic_publication_date']
