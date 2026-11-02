import base64,copy,json,os
from pathlib import Path
import requests
PATH=Path('state/remotion_registry.json')
REPOS={'science-discovery-shorts':'science','documented-history-stories':'history','arabic-horror-stories':'horror','ai-news-daily':'news','stickman-what-if-shorts':'stickman'}
def identity():
 repo=os.environ['GITHUB_REPOSITORY'];owner,name=repo.split('/')
 if owner!='ahmedalsharqwi2-gif' or name not in REPOS:raise ValueError('Repository identity is not an authorized channel')
 return repo,REPOS[name]
def local():return json.loads(PATH.read_text()) if PATH.exists() else {'version':1,'episodes':{}}
def mutate(update):
 if os.getenv('GITHUB_ACTIONS')!='true':
  data=local();update(data);PATH.parent.mkdir(exist_ok=True);PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');return data
 repo,_=identity();token=os.environ['GITHUB_TOKEN'];url=f'https://api.github.com/repos/{repo}/contents/{PATH.as_posix()}'
 headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'}
 for _ in range(3):
  response=requests.get(url,params={'ref':'main'},headers=headers,timeout=30)
  if response.status_code==404:data={'version':1,'episodes':{}};sha=None
  else:
   response.raise_for_status();body=response.json();data=json.loads(base64.b64decode(body['content']));sha=body['sha']
  candidate=copy.deepcopy(data);update(candidate)
  if any(k not in candidate['episodes'] for k in data['episodes']):raise ValueError('Episode history cannot be deleted')
  content=json.dumps(candidate,ensure_ascii=False,indent=2)+'\n'
  payload={'message':'Preserve Remotion episode intent and exact production evidence [skip ci]','branch':'main','content':base64.b64encode(content.encode()).decode()}
  if sha:payload['sha']=sha
  saved=requests.put(url,headers=headers,json=payload,timeout=30)
  if saved.status_code in (409,422):continue
  saved.raise_for_status();PATH.parent.mkdir(exist_ok=True);PATH.write_text(content);return candidate
 raise RuntimeError('Durable state conflict; provider calls remain blocked')
