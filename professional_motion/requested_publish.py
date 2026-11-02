"""Publish an explicitly requested verified episode; metadata edits never rewrite its voice."""
import argparse,copy,json
from pathlib import Path
from . import metadata
from .publisher import publish
def main():
 p=argparse.ArgumentParser();p.add_argument('profile');p.add_argument('--slot',required=True);p.add_argument('--due',required=True);p.add_argument('--request',default='.github/produce-new-today.json');a=p.parse_args()
 request=json.loads(Path(a.request).read_text());original=metadata.make
 def make(story,profile):
  revised=copy.deepcopy(story)
  if request.get('publication_title'):revised['title']=request['publication_title']
  result=original(revised,profile)
  if story.get('source',{}).get('kind') in ('general_knowledge','original_fiction'):
   result['caption']='\n'.join(line for line in result['caption'].splitlines() if not line.strip().startswith('المصدر:'))
  return result
 metadata.make=make
 try:publish(a.profile,a.slot,a.due)
 finally:metadata.make=original
if __name__=='__main__':main()
