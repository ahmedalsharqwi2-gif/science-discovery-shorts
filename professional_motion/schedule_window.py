"""Same-day Cairo production window with a short safety buffer before publication."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
CAIRO=ZoneInfo('Africa/Cairo')
def daily_window(now):
 if now.tzinfo is None:raise ValueError('A timezone-aware clock is required')
 local=now.astimezone(CAIRO)
 due=local.replace(hour=17,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
 reason='before_window' if local.hour<9 else 'window_closed' if (local.hour>16 or (local.hour==16 and local.minute>=30)) else 'eligible'
 return reason,due,'daily-'+local.date().isoformat()
