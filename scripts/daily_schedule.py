"""One daily publication slot: 17:00 Africa/Cairo, including DST transitions."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json, os
CAIRO=ZoneInfo('Africa/Cairo')

def next_slot(now=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('Publication clock must be timezone-aware')
    local=now.astimezone(CAIRO)
    due=local.replace(hour=17,minute=0,second=0,microsecond=0)
    if due<=local:due+=timedelta(days=1)
    return due.astimezone(timezone.utc)

def validate_slot(value,now=None):
    due=datetime.fromisoformat(value.replace('t','T').replace('z','Z').replace('Z','+00:00'))
    if due.tzinfo is None:raise ValueError('Publication time requires a timezone')
    local=due.astimezone(CAIRO)
    if (local.hour,local.minute,local.second)!=(17,0,0):raise ValueError('Publication must be exactly 17:00 Cairo')
    if due<=(now or datetime.now(timezone.utc)):raise ValueError('Publication slot already passed; never publish immediately as a fallback')
    return due

def plan():
    due=next_slot();local=due.astimezone(CAIRO);key=f'stock {local.date()} 17 Cairo'
    path=Path('state/publication_stock.json')
    data=json.loads(path.read_text()) if path.exists() else {}
    entry=data.get('slots',{}).get(key,{})
    required=entry.get('required_services',[])
    confirmed=entry.get('confirmed') is True and bool(required) and all(entry.get('receipts',{}).get(s,{}).get('id') for s in required)
    values={'PUBLISH_DUE_AT':due.isoformat(timespec='seconds').replace('+00:00','Z'),'PUBLISH_DATE':str(local.date()),'PUBLISH_HOUR':'17','PUBLISH_IMMEDIATE':'false'}
    if os.getenv('GITHUB_ENV'):
        with open(os.environ['GITHUB_ENV'],'a') as f:
            for k,v in values.items():f.write(f'{k}={v}\n')
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write(f'already_confirmed={str(confirmed).lower()}\n')
    print(json.dumps({**values,'already_confirmed':confirmed},indent=2))
if __name__=='__main__':plan()
