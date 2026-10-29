"""Prepare one new subject, render for review, then conditionally schedule it."""
import argparse,hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .editorial import prepare,rendered
from .publisher import approved,preflight,publish
from scripts.daily_schedule import next_slot


def decision(profile,mode,event,now=None):
    now=now or datetime.now(timezone.utc);local=now.astimezone(ZoneInfo('Africa/Cairo'))
    daily=mode=='daily' or event=='schedule'
    enabled=approved()
    # Two UTC cron hours cover both Cairo offsets. The civil-time guard selects one.
    run=not daily or (enabled and (event!='schedule' or local.hour==9))
    due=next_slot(now).isoformat(timespec='seconds').replace('+00:00','Z')
    slot=('daily-'+due[:10]) if daily else 'review-'+os.getenv('GITHUB_RUN_ID','local')
    return {'run':run,'publish':daily and enabled,'due':due,'slot':slot,'profile':profile,'approval_pending':daily and not enabled}


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['decision','prepare','preflight','rendered','publish']);p.add_argument('profile',choices=['science','horror','history','news']);p.add_argument('--mode',default='review');p.add_argument('--slot',default=os.getenv('EPISODE_SLOT'));p.add_argument('--due',default=os.getenv('PUBLISH_DUE_AT'));a=p.parse_args()
    if a.action=='decision':
        d=decision(a.profile,a.mode,os.getenv('GITHUB_EVENT_NAME','workflow_dispatch'))
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:
                for k,v in d.items():f.write(k+'='+str(v).lower()+'\n')
        print(json.dumps(d));return
    if a.action=='prepare':
        from .credentials import preflight as generation_credentials
        generation_credentials();prepare(a.profile,a.slot)
    elif a.action=='preflight':preflight(a.profile)
    elif a.action=='rendered':rendered(a.slot,Path(__file__).resolve().parent/'output/professional-review.mp4')
    else:publish(a.profile,a.slot,a.due)


if __name__=='__main__':main()
