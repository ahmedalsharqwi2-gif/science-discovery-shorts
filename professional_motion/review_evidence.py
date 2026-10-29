"""Deliver safe narration evidence on an isolated, append-only review branch."""
import json,os,subprocess
from pathlib import Path

def git(*args,data=None):return subprocess.check_output(['git',*args],input=data).decode().strip()
p=Path('professional_motion/delivery');p.mkdir(exist_ok=True)
status={'run_id':os.environ['GITHUB_RUN_ID'],'stage':os.getenv('REVIEW_STAGE','voice'),'review_only':os.getenv('REVIEW_ONLY','true')=='true'}
(p/'status.json').write_text(json.dumps(status))
entries=[]
for path in sorted(p.glob('*')):
    if not path.is_file() or (path.suffix!='.json' and path.name!='narration.wav'):continue
    entries.append('100644 blob '+git('hash-object','-w',str(path))+'\t'+path.name+'\n')
if not entries:raise ValueError('No review evidence')
leaf=git('mktree',data=''.join(entries).encode());mid=git('mktree',data=('040000 tree '+leaf+'\tdelivery\n').encode());tree=git('mktree',data=('040000 tree '+mid+'\tprofessional_motion\n').encode())
branch='codex/professional-review-run-'+os.environ['GITHUB_RUN_ID'];parent=[]
exists=subprocess.run(['git','ls-remote','--exit-code','origin','refs/heads/'+branch],capture_output=True)
if exists.returncode==0:
    git('fetch','origin','refs/heads/'+branch);parent=['-p',git('rev-parse','FETCH_HEAD')]
commit=git('-c','user.name=review-evidence-bot','-c','user.email=bot@users.noreply.github.com','commit-tree',tree,*parent,'-m','Safe original narration and measured review evidence [skip ci]')
git('push','origin',commit+':refs/heads/'+branch)
