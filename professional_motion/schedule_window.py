"""Same-day Cairo production window with a short safety buffer before publication."""
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
CAIRO=ZoneInfo('Africa/Cairo')
def daily_window(now):
 if now.tzinfo is None:raise ValueError('A timezone-aware clock is required')
 local=now.astimezone(CAIRO)
 due=(local+timedelta(days=1)).replace(hour=17,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
 reason='eligible'
 return reason,due,'daily-'+local.date().isoformat()
