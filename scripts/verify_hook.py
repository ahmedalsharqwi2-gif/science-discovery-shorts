"""Verify the delivered ASS opening, independently of the episode declaration."""
import argparse,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from visual_contract import load_template,validate_hook

def verify(path,hook):
 events=[]
 for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
  if line.startswith('Dialogue:'):
   fields=line.split(',',9)
   if len(fields)!=10:raise ValueError('Malformed Dialogue')
   text=re.sub(r'\{[^}]*\}','',fields[9]).replace(r'\N',' ').replace(r'\n',' ').replace(r'\h',' ')
   h,m,s=fields[1].split(':');start=int(h)*3600+int(m)*60+float(s)
   events.append((start,text))
 if not events or events[0]!=(0,hook):raise ValueError('First Dialogue must be the exact hook at 0:00:00.00')
 if min(x[0] for x in events)<0:raise ValueError('Event before the hook')
 return {'passed':True,'hook_line':hook,'starts_at':0}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('ass',type=Path);a.add_argument('--story',type=Path,required=True);args=a.parse_args();story=json.loads(args.story.read_text());t=load_template();validate_hook(story['hook_line'],max_words=t['hook']['max_words'],profile=t['channel'],source_terms=story.get('hook_source_terms',()));print(json.dumps(verify(args.ass,story['hook_line']),ensure_ascii=False))
