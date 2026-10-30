"""Expand the same reserved short daily topic against its real source; no substitute film."""
import json
from . import editorial as e

def main():
 data=e.registry();episode=next(r for r in data['episodes'] if r['slot']=='daily-2026-10-30')
 if episode.get('status') in ('scheduled','published'):raise RuntimeError('Do not alter a scheduled film')
 old=episode['story'];row=next(r for r in e.candidates('science') if r['key']==old['topic_key'])
 previous=[{'subject':r.get('canonical_subject',r.get('topic_key','')),'title':r.get('title','')} for r in data['episodes'] if r is not episode]
 story=e.write_sourced(row,'science',previous)
 if len(' '.join(s['narration'] for s in story['scenes']).split())<290:raise ValueError('Science expansion still too short; keep the old reserved story unchanged')
 episode.update(story=story,title=story['title'],status='reserved',revision_reason='Original narration measured 106.6 seconds; source-backed expansion to reach the requested two-minute daily film')
 e.save(data);(e.ROOT/'delivery').mkdir(exist_ok=True);(e.ROOT/'delivery/story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2))
 print('Expanded the same reserved science topic; no new topic reservation')
if __name__=='__main__':main()
