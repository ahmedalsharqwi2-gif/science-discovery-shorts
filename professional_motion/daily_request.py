"""Freeze a run's next-day Cairo publication target, including workflow reruns."""
import json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
CAIRO=ZoneInfo('Africa/Cairo')

def target(profile,repository,created_at,now,*,event,cron=None):
    if created_at.tzinfo is None or now.tzinfo is None:raise ValueError('Timezone-aware clocks required')
    local=created_at.astimezone(CAIRO)
    if event=='schedule':
        expected=f"0 {9-int(local.utcoffset().total_seconds()/3600)} * * *"
        if cron!=expected or not 9<=local.hour<12:return None
    due=(local+timedelta(days=1)).replace(hour=17,minute=0,second=0,microsecond=0).astimezone(timezone.utc)
    if due<=now:raise ValueError('Original publication slot expired; refusing automatic rollover')
    return {'request_id':'daily-'+local.date().isoformat(),'repository':repository.rsplit('/',1)[-1],
        'profile':profile,'slot':'daily-'+local.date().isoformat(),'due_at':due.isoformat(timespec='seconds').replace('+00:00','Z'),
        'new_topic_required':True,'production_timezone':'Africa/Cairo','run_created_at':created_at.isoformat()}

def main():
    import argparse,requests
    p=argparse.ArgumentParser();p.add_argument('profile');a=p.parse_args()
    repo=os.environ['GITHUB_REPOSITORY'];run=os.environ['GITHUB_RUN_ID']
    response=requests.get(f'https://api.github.com/repos/{repo}/actions/runs/{run}',headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'},timeout=30)
    response.raise_for_status();created=datetime.fromisoformat(response.json()['created_at'].replace('Z','+00:00'))
    event=json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    request=target(a.profile,repo,created,datetime.now(timezone.utc),event=os.environ['GITHUB_EVENT_NAME'],cron=event.get('schedule'))
    if request is None:
        with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('eligible=false\n')
        print('Other Cairo DST cron or production window closed; no work requested');return
    request['source_run']=int(run)
    if os.environ['GITHUB_EVENT_NAME']!='schedule' and event.get('inputs',{}).get('mode','review')!='daily':
        request.update(review_only=True,request_id='review-'+run,slot='review-'+run)
    path=Path('.work/daily-request.json');path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
    with open(os.environ['GITHUB_OUTPUT'],'a') as output:output.write('eligible=true\n')
    print(json.dumps(request))
if __name__=='__main__':main()
