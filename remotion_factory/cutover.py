"""Record evidence for cron cutover; workflow edits use the connected GitHub app."""
from .state import mutate
from .prepare import read_request

def main():
 req=read_request()
 def ready(data):
  entry=data['episodes'][req['slot']]
  if entry['status']!='scheduled' or len(entry.get('receipts',{}))!=3 or not all(r.get('phase')=='verified' for r in entry['receipts'].values()):raise ValueError('Full film and three independently verified receipts required before cutover')
  data['cutover_evidence']={'slot':req['slot'],'video_sha256':entry['video_sha256'],'run':entry['render_run'],'ready':True}
 mutate(ready)
 print('Full film and verified receipts recorded; legacy workflow bytes remain preserved')
if __name__=='__main__':main()
