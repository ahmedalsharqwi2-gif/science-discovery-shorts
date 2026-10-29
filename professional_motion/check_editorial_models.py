"""Read provider model names only; never print credential values or error bodies."""
import json,os,subprocess
from pathlib import Path
import requests
key=(os.getenv('GEMINI_TEXT_API_KEY') or os.getenv('GEMINI_API_KEY') or '').strip()
if not key:raise RuntimeError('Repository writing credential is missing')
rows=[];page=''
for _ in range(5):
 params={'pageSize':1000}
 if page:params['pageToken']=page
 r=requests.get('https://generativelanguage.googleapis.com/v1beta/models',headers={'x-goog-api-key':key},params=params,timeout=45)
 if r.status_code!=200:raise RuntimeError('Model catalog HTTP '+str(r.status_code))
 d=r.json()
 rows +=[{'name':x.get('name','').removeprefix('models/'),'methods':x.get('supportedGenerationMethods',[])} for x in d.get('models',[]) if 'generateContent' in x.get('supportedGenerationMethods',[]) and 'gemini' in x.get('name','')]
 page=d.get('nextPageToken','')
 if not page:break
from api_budget import reserve
probes=[]
for model in ('gemini-3.8-flash','gemini-4-argon','gemini-3.1-pro-preview'):
 if not any(row['name']==model for row in rows):continue
 reserve('text',model,key)
 r=requests.post('https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent',headers={'x-goog-api-key':key},json={'contents':[{'parts':[{'text':'Return only JSON {"ready":true}.'}]}],'generationConfig':{'responseMimeType':'application/json','responseSchema':{'type':'OBJECT','properties':{'ready':{'type':'BOOLEAN'}},'required':['ready']},'maxOutputTokens':2048}},timeout=120)
 ok=False
 if r.status_code==200:
  c=r.json().get('candidates',[{}])[0]
  try:ok=json.loads(''.join(x.get('text','') for x in c.get('content',{}).get('parts',[]) if not x.get('thought'))).get('ready') is True
  except ValueError:pass
 probes.append({'model':model,'http_status':r.status_code,'json_generation_confirmed':ok})
p=Path('model-catalog.json');p.write_text(json.dumps({'models':rows,'generation_probes':probes},indent=2))
def git(*args,data=None):return subprocess.check_output(['git',*args],input=data).decode().strip()
b=git('hash-object','-w',str(p));tree=git('mktree',data=('100644 blob '+b+'\tmodel-catalog.json\n').encode());c=git('-c','user.name=model-catalog-bot','-c','user.email=bot@users.noreply.github.com','commit-tree',tree,'-m','Safe editorial model capability catalog [skip ci]');git('push','origin',c+':refs/heads/codex/editorial-models-'+os.environ['GITHUB_RUN_ID'])
print('Catalog saved; credential values were not included')
