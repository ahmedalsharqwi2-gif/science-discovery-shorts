"""Immutable per-episode documents keep the daily registry small over years."""
import base64,hashlib,json,os
from pathlib import Path
import requests
from .state import identity
def write(slot,kind,value):
 raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();path='state/remotion_documents/'+slot+'-'+kind+'-'+digest[:16]+'.json'
 if os.getenv('GITHUB_ACTIONS')=='true':
  repo,_=identity();h={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'};url='https://api.github.com/repos/'+repo+'/contents/'+path
  r=requests.get(url,headers=h,params={'ref':'main'},timeout=30)
  if r.status_code==404:
   r=requests.put(url,headers=h,json={'message':'Retain immutable original Remotion '+kind+' [skip ci]','branch':'main','content':base64.b64encode(raw).decode()},timeout=30);r.raise_for_status()
  else:
   r.raise_for_status()
   if hashlib.sha256(base64.b64decode(r.json()['content'])).hexdigest()!=digest:raise ValueError('Immutable episode document changed')
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);return {'path':path,'sha256':digest}
def read(reference):
 p=Path(reference['path'])
 if not str(p).startswith('state/remotion_documents/') or '..' in p.parts:raise ValueError('Invalid retained document path')
 if not p.exists():
  repo,_=identity();r=requests.get('https://api.github.com/repos/'+repo+'/contents/'+p.as_posix(),headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'},params={'ref':'main'},timeout=30);r.raise_for_status();raw=base64.b64decode(r.json()['content'])
 else:raw=p.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('Retained document fingerprint mismatch')
 return json.loads(raw)
