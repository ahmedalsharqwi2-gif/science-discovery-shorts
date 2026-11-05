"""Retrieve the explicitly approved unreferenced Git object and host exact bytes in Releases."""
import base64,hashlib,json,os,subprocess
from pathlib import Path
import requests
def main():
 r=json.loads(Path('.github/replace-noon-request.json').read_text());repo=os.environ['GITHUB_REPOSITORY'];assert repo==r['repository'] and r['owner_approved_exact_full_file'] and r['owner_approved_git_blob_transport']
 headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json'};api='https://api.github.com/repos/'+repo
 release=requests.get(api+'/releases/tags/approved-identity-2026-11-05',headers=headers,timeout=40);release.raise_for_status();release=release.json();old=next((x for x in release['assets'] if x['name']=='identity-full-review.mp4'),None)
 if old:
  if old.get('digest')!='sha256:'+r['new_video_sha256']:raise ValueError('Existing release asset fingerprint differs; do not overwrite')
  print('Exact approved release asset already present');return
 p=Path('/tmp/approved-transport/identity-full-review.mp4');p.parent.mkdir(exist_ok=True)
 with p.open('wb') as out:
  for part in r['transport_parts']:
   blob=requests.get(api+'/git/blobs/'+part['blob_sha'],headers=headers,timeout=180);blob.raise_for_status();data=blob.json();assert data['encoding']=='base64' and data['sha']==part['blob_sha'];raw=base64.b64decode(data['content']);assert hashlib.sha256(raw).hexdigest()==part['sha256'];out.write(raw)
 assert hashlib.sha256(p.read_bytes()).hexdigest()==r['new_video_sha256']
 env=dict(os.environ,GH_TOKEN=os.environ['GITHUB_TOKEN']);subprocess.run(['gh','release','upload','approved-identity-2026-11-05',str(p),'-R',repo],env=env,check=True)
 check=requests.get(api+'/releases/tags/approved-identity-2026-11-05',headers=headers,timeout=40);check.raise_for_status();asset=next(x for x in check.json()['assets'] if x['name']==p.name)
 if asset.get('digest')!='sha256:'+r['new_video_sha256'] or asset['browser_download_url']!=r['new_media_url']:raise ValueError('Hosted approved asset digest/URL not independently confirmed')
 print(json.dumps({'hosted_exact_sha256':r['new_video_sha256'],'git_branch_paths_added_for_media':0}))
if __name__=='__main__':main()
