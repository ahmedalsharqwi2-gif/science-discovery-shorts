"""Report fixed-category workflow failure facts, never original log text."""
import json,os,re,urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY'];run=os.environ['INSPECT_RUN'];token=os.environ['GITHUB_TOKEN']
def get(path):
 req=urllib.request.Request('https://api.github.com'+path,headers={'Accept':'application/vnd.github+json'})
 req.add_unredirected_header('Authorization','Bearer '+token)
 return urllib.request.urlopen(req,timeout=45).read()
report={'inspected_run':run,'raw_log_exposed':False,'jobs':[]}
try:jobs=json.loads(get(f'/repos/{repo}/actions/runs/{run}/jobs'))['jobs']
except Exception as error:jobs=[];report['metadata_error']={'type':type(error).__name__,'http_status':getattr(error,'code',None)}
for job in jobs:
 if job['name']!='produce':continue
 try:raw=get(f'/repos/{repo}/actions/jobs/{job["id"]}/logs').decode(errors='replace')
 except Exception as error:report['jobs'].append({'log_access_error':type(error).__name__,'http_status':getattr(error,'code',None)});continue
 known=['BudgetExceeded','RuntimeError','ValueError','KeyError','HTTPError','ReadTimeout','ConnectionError','JSONDecodeError']
 report['jobs'].append({'conclusion':job['conclusion'],'error_classes':[x for x in known if re.search(r'\b'+x+r':',raw)],'editorial_http_codes':sorted(set(re.findall(r'Editorial provider HTTP ([0-9]{3})',raw))),'local_safety_budget_reached':'local safety budget reached' in raw,'incomplete_editorial_response':'Incomplete editorial response' in raw,'no_unused_topic':'No unused, evidence-backed topic' in raw,'missing_generation_secret':'Missing repository Actions secret' in raw,'failed_steps':[s['name'] for s in job['steps'] if s['conclusion']=='failure']})
p=Path('professional_motion/delivery');p.mkdir(parents=True,exist_ok=True);(p/'safe-failure-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
