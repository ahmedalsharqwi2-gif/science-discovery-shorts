"""Persist only durable episode/publication state; never stage generated media."""
import os,subprocess,time
from pathlib import Path

def run(*args):return subprocess.run(['git',*args],check=True)
run('config','user.name','content-factory-bot');run('config','user.email','bot@users.noreply.github.com')
for name in ['state/professional_topics.json','state/publication_stock.json','state/yt_token_last_success.json']:
    if Path(name).exists():run('add',name)
if subprocess.run(['git','diff','--cached','--quiet']).returncode:
    run('commit','-m','Persist professional episode and publication receipts [skip ci]')
    for attempt in range(3):
        if subprocess.run(['git','pull','--rebase','--autostash','origin',os.environ['GITHUB_REF_NAME']]).returncode==0 and subprocess.run(['git','push','origin','HEAD:refs/heads/'+os.environ['GITHUB_REF_NAME']]).returncode==0:break
        time.sleep(3)
    else:raise RuntimeError('Could not persist durable production state')
