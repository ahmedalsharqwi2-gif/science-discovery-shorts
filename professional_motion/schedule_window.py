"""Legacy entrypoint guard: produce from09Cairo with a short queue-delay allowance."""
from datetime import timezone,timedelta
from zoneinfo import ZoneInfo
CAIRO=ZoneInfo('Africa/Cairo')
def daily_window(now):
 if now.tzinfo is None:raise ValueError('A timezone-aware clock is required')
 local=now.astimezone(CAIRO)
 due=(local+timedelta(days=1)).replace(hour=17,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
 return ('eligible' if 9<=local.hour<12 else 'window_closed'),due,'daily-'+local.date().isoformat()
