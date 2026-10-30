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
    if daily and os.getenv('GITHUB_ACTIONS')=='true' and os.getenv('GITHUB_REF_NAME')!='main':raise PermissionError('Daily production uses main durable state only')
    enabled=approved()
    from .schedule_window import daily_window
    from .editorial import registry
    reason,due_at,slot=daily_window(now)
    due=due_at.isoformat(timespec='seconds').replace('+00:00','Z')
    existing=next((r for r in registry()['episodes'] if r.get('slot')==slot),None) if daily else None
    complete=bool(existing and existing.get('status') in ('scheduled','published') and len(existing.get('receipts',{}))==3 and all(r.get('id') for r in existing['receipts'].values()))
    run=not daily or (enabled and reason=='eligible' and not complete)
    if complete:reason='already_scheduled'
    return {'run':run,'publish':daily and enabled and run,'due':due,'slot':slot if daily else 'review-'+os.getenv('GITHUB_RUN_ID','local'),'profile':profile,'approval_pending':daily and not enabled,'reason':reason}


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['decision','prepare','preflight','rendered','publish']);p.add_argument('profile',choices=['science','horror','history','news']);p.add_argument('--mode',default='review');p.add_argument('--slot',default=os.getenv('EPISODE_SLOT'));p.add_argument('--due',default=os.getenv('PUBLISH_DUE_AT'));a=p.parse_args()
    if a.action=='decision':
        d=decision(a.profile,a.mode,os.getenv('GITHUB_EVENT_NAME','workflow_dispatch'))
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a') as f:
                for k,v in d.items():f.write(k+'='+(str(v).lower() if isinstance(v,bool) else str(v))+'\n')
        print(json.dumps(d))
        if d['reason']=='window_closed' and (a.mode=='daily' or os.getenv('GITHUB_EVENT_NAME')=='schedule'):
            raise RuntimeError('Production window closed; no immediate posting or next-day rollover')
        return
    if a.action=='prepare':
        from .credentials import preflight as generation_credentials
        generation_credentials();prepare(a.profile,a.slot)
    elif a.action=='preflight':preflight(a.profile)
    elif a.action=='rendered':rendered(a.slot,Path(__file__).resolve().parent/'output/professional-review.mp4')
    else:publish(a.profile,a.slot,a.due)


if __name__=='__main__':main()
