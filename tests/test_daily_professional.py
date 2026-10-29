import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from professional_motion.cli import decision
from professional_motion import editorial as e
from professional_motion.publisher import approved

class DailyProfessionalTests(unittest.TestCase):
 def test_review_never_publishes_even_when_release_is_approved(self):
  with patch('professional_motion.cli.approved',return_value=True):
   d=decision('history','review','workflow_dispatch');self.assertTrue(d['run']);self.assertFalse(d['publish'])
 def test_no_input_bypasses_pending_human_review(self):
  with patch('professional_motion.cli.approved',return_value=False):
   for event in ('schedule','workflow_dispatch'):
    d=decision('horror','daily',event);self.assertFalse(d['run']);self.assertFalse(d['publish'])
 def test_cairo_noon_guard_selects_one_utc_cron_in_each_season(self):
  with patch('professional_motion.cli.approved',return_value=True):
   for month,hour in ((7,9),(12,10)):
    d=decision('science','daily','schedule',datetime(2026,month,1,hour,tzinfo=timezone.utc));self.assertTrue(d['run'])
    wrong=decision('science','daily','schedule',datetime(2026,month,1,hour+1,tzinfo=timezone.utc));self.assertFalse(wrong['run'])
 def test_scheduled_due_is_exactly_five_cairo_including_dst_transition(self):
  from zoneinfo import ZoneInfo
  with patch('professional_motion.cli.approved',return_value=True):
   for day in (28,29,30,31):
    d=decision('news','daily','schedule',datetime(2026,10,day,10,tzinfo=timezone.utc))
    due=datetime.fromisoformat(d['due'].replace('Z','+00:00')).astimezone(ZoneInfo('Africa/Cairo'))
    self.assertEqual((due.hour,due.minute,due.second),(17,0,0))
 def test_url_aliases_cannot_bypass_source_deduplication(self):
  self.assertEqual(e.canonical('https://science.nasa.gov/moon/?campaign=1#top'),e.canonical('https://science.nasa.gov/moon'))
  with self.assertRaises(ValueError):e.canonical('https://science.nasa.gov.attacker.example/moon')
 def test_reserved_slot_reuses_its_story_without_new_provider_calls(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'state.json';story={'title':'مصدر جديد','topic_key':'one'}
   state.write_text(json.dumps({'version':2,'episodes':[{'slot':'daily-one','status':'reserved','story':story}]}))
   with patch.object(e,'STATE',state),patch.object(e,'ROOT',root),patch.object(e,'ask',side_effect=AssertionError('must not ask twice')):
    self.assertEqual(e.prepare('science','daily-one'),story)
 def test_a_scheduled_daily_slot_cannot_create_another_episode(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'state.json';state.write_text(json.dumps({'version':2,'episodes':[{'slot':'one','status':'scheduled'}]}))
   with patch.object(e,'STATE',state),patch.object(e,'ROOT',root):
    with self.assertRaisesRegex(RuntimeError,'confirmed'):e.prepare('science','one')
 def test_approval_requires_actual_sample_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'release.json';p.write_text(json.dumps({'style_approved':True,'publication_approved':True}))
   with patch('professional_motion.publisher.POLICY',p):self.assertFalse(approved())

 def test_legacy_provenance_strings_do_not_crash_novelty_checks(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td)
   with patch.object(e,'STATE',root/'registry.json'),patch.object(e,'ROOT',root),patch.object(e,'prior',return_value=[{'source':'git-history-backfill','title':'old subject'}]),patch.object(e,'candidates',return_value=[]):
    with self.assertRaisesRegex(RuntimeError,'No unused'):e.prepare('horror','new-slot')

 def test_legacy_ids_are_mapped_by_provider_service_not_positional_guess(self):
  from professional_motion.publisher import verified_mapping
  rows=[{'id':'a','service':'tiktok','name':'ملفات غامضه'},{'id':'b','service':'youtube','name':'ملفات غامضة'},{'id':'c','service':'facebook','name':'ملفات غامضه'}]
  with patch.dict(os.environ,{'BUFFER_CHANNEL_IDS':'a,b,c'},clear=True):
   self.assertEqual(verified_mapping('horror',rows),{'tiktok':'a','youtube':'b','facebook':'c'})
 def test_a_valid_id_for_an_unrelated_brand_is_rejected(self):
  from professional_motion.publisher import verified_mapping
  rows=[{'id':'a','service':'facebook','name':'اسرار الكون'}]
  with patch.dict(os.environ,{'BUFFER_CHANNEL_IDS':'a'},clear=True):
   with self.assertRaisesRegex(ValueError,'brand'):verified_mapping('news',rows)
 def test_explicit_channel_service_must_match_provider(self):
  from professional_motion.publisher import verified_mapping
  rows=[{'id':'a','service':'facebook','name':'اسرار الكون'}]
  with patch.dict(os.environ,{'BUFFER_YOUTUBE_CHANNEL_ID':'a'},clear=True):
   with self.assertRaises(ValueError):verified_mapping('science',rows)

 def test_generic_numbered_slides_are_not_a_topic_specific_film(self):
  story={'suitable':True,'title':'موضوع جديد','scenes':[{'label':'الشريحة الأولى','narration':'ده مش مجرد لون عشان اللي قدامك جزء من موضوع علمي جديد','labels':[]} for _ in range(8)]}
  with self.assertRaisesRegex(ValueError,'topic-specific'):e.validate(story,'science',{'family':'space'})

class ExactSourceSelectionTests(unittest.TestCase):
 def test_indexed_excerpts_keep_the_original_source_words(self):
  source=' '.join('sourceword'+str(i) for i in range(45))
  story={'scenes':[{'evidence_excerpt_id':1}]};e.attach_evidence(story,source)
  self.assertEqual(story['scenes'][0]['evidence_quote'],' '.join(source.split()[15:30]))
 def test_invalid_excerpt_ids_cannot_invent_evidence(self):
  for index in (True,-1,20,'1'):
   with self.assertRaises(ValueError):e.attach_evidence({'scenes':[{'evidence_excerpt_id':index}]},'one two three four five six seven eight nine ten')

class EvidenceAndTimingTests(unittest.TestCase):
 def test_a_fabricated_source_quote_is_rejected(self):
  with self.assertRaises(ValueError):e.verify_evidence({'scenes':[{'evidence_quote':'this invented quotation is not in source'}]},'An actual source with different statements.')
 def test_conflicting_models_use_a_monotonic_exact_match_chain(self):
  from professional_motion.alignment import measured_timing
  words='ده شرح جديد عن القوس اللي بيحمل حجر عشان نفهم شكله'.split()
  story={'scenes':[{'narration':' '.join(words)}]}
  a=[{'text':w,'start':float(i),'end':i+.5} for i,w in enumerate(words)]
  bad=[{**w,'start':w['start']+(.1 if i%2 else 2),'end':w['end']+(.1 if i%2 else 2)} for i,w in enumerate(a)]
  t=measured_timing(story,20,[('one',bad),('two',a)])
  self.assertEqual(t['coverage'],1)
  self.assertTrue(all(x['start']<=x['end'] for x in t['caption_groups']))

if __name__=='__main__':unittest.main()
