"""Prepare on the previous Cairo civil day; keep each publication target immutable."""
from datetime import date, datetime, time, timedelta, timezone
import math
from zoneinfo import ZoneInfo

CAIRO=ZoneInfo('Africa/Cairo')

def window(now:datetime,publication_date=None)->dict:
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError('A timezone-aware current time is required')
    local=now.astimezone(CAIRO)
    target=local.date()+timedelta(days=1) if publication_date is None else date.fromisoformat(publication_date) if isinstance(publication_date,str) else publication_date
    if isinstance(target,datetime) or not isinstance(target,date):
        raise ValueError('An explicit Cairo publication date is required')
    preparation_day=target-timedelta(days=1)
    due=datetime.combine(target,time(17),CAIRO)
    start=datetime.combine(preparation_day,time(9),CAIRO)
    cutoff=datetime.combine(target,time(15),CAIRO)
    reason='too_early' if local<start else 'missed' if local>=cutoff else 'eligible'
    return {'reason':reason,'run':reason=='eligible','slot':'daily-'+target.isoformat(),
            'preparation_date':preparation_day.isoformat(),'publication_date':target.isoformat(),
            'due_at':due.astimezone(timezone.utc).isoformat().replace('+00:00','Z')}

def require_duration(seconds:float)->float:
    value=float(seconds)
    if not math.isfinite(value) or not 120<=value<180:
        raise ValueError('Daily films must be at least 120 and less than 180 seconds')
    return value

def require_future_due(due:str,now:datetime)->datetime:
    value=datetime.fromisoformat(due.replace('Z','+00:00'))
    if value.tzinfo is None or now.tzinfo is None:
        raise ValueError('Absolute timezone-aware due and current times required')
    if value<=now:raise ValueError('Publication slot missed; no immediate posting or silent rollover')
    local=value.astimezone(CAIRO);today=now.astimezone(CAIRO).date()
    if (local.hour,local.minute,local.second,local.microsecond)!=(17,0,0,0):
        raise ValueError('Publication must target exactly 17:00 Cairo')
    if local.date() not in (today,today+timedelta(days=1)):
        raise ValueError('Only the retained current-day or next-day Cairo publication target can be scheduled')
    return value
