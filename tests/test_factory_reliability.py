import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from professional_motion.cli import decision
from professional_motion import editorial
from professional_motion.receipt_verification import verify_scheduled

class FactoryReliabilityTests(unittest.TestCase):
 def decide(self,month,hour,minute=0,episodes=None):
  with patch('professional_motion.cli.approved',return_value=True),patch('professional_motion.editorial.registry',return_value={'episodes':episodes or []}):
   return decision('science','daily','schedule',datetime(2026,month,1,hour,minute,tzinfo=timezone.utc))
 def test_delayed_run_and_summer_winter_have_same_cairo_publication_hour(self):
  from zoneinfo import ZoneInfo
  for month,hour in ((7,8),(12,9)):
   result=self.decide(month,hour,45);self.assertTrue(result['run'])
   self.assertEqual(datetime.fromisoformat(result['due'].replace('Z','+00:00')).astimezone(ZoneInfo('Africa/Cairo')).hour,17)
 def test_late_start_is_blocked_and_does_not_roll_to_tomorrow(self):
  r=self.decide(12,15);self.assertFalse(r['run']);self.assertFalse(r['publish']);self.assertEqual(r['due'][:10],'2026-12-01')
 def test_production_cutoff_leaves_two_hours_for_delivery(self):
  self.assertTrue(self.decide(12,12,59)['run']);self.assertFalse(self.decide(12,13)['run'])
 def test_second_daily_run_skips_three_confirmed_receipts(self):
  first=self.decide(12,7)
  existing={'slot':first['slot'],'status':'scheduled','receipts':{k:{'id':k} for k in ('youtube','facebook','instagram')}}
  second=self.decide(12,9,episodes=[existing]);self.assertFalse(second['run']);self.assertEqual(second['reason'],'already_scheduled')
 def test_partial_receipts_are_not_reported_as_completed(self):
  first=self.decide(12,7)
  self.assertTrue(self.decide(12,9,episodes=[{'slot':first['slot'],'status':'scheduled','receipts':{'youtube':{'id':'one'}}}])['run'])
 def test_missing_mp4_cannot_be_marked_rendered(self):
  with patch.object(editorial,'registry',return_value={'episodes':[{'slot':'today','status':'reserved'}]}),patch.object(editorial,'save') as save:
   with self.assertRaises(FileNotFoundError):editorial.rendered('today',Path('/tmp/nonexistent-factory-movie.mp4'))
   save.assert_not_called()
 def test_tts_outage_stops_before_rendering_or_alignment(self):
  from professional_motion import voice_job
  with tempfile.TemporaryDirectory() as td:
   original=os.getcwd();os.chdir(td)
   try:
    p=Path('professional_motion/delivery');p.mkdir(parents=True);(p/'story.json').write_text(json.dumps({'profile':'science','scenes':[{'narration':'نص عربي جديد'}]}))
    with patch.object(voice_job,'generate',side_effect=RuntimeError('Gemini TTS unavailable')):
     with self.assertRaisesRegex(RuntimeError,'unavailable'):voice_job.main()
    self.assertFalse((p/'timing.json').exists())
   finally:os.chdir(original)
 def test_provider_receipt_requires_actual_scheduled_state_and_due_time(self):
  mapping={'youtube':'yt','facebook':'fb','instagram':'ig'};receipts={k:{'id':k} for k in mapping};due='2026-12-01T15:00:00Z'
  def response(query):
   service=next(k for k in mapping if '"'+k+'"' in query)
   return {'post':{'id':service,'status':'scheduled','dueAt':due}}
  with patch('professional_motion.receipt_verification.query',side_effect=response):
   verified=verify_scheduled(receipts,mapping,due);self.assertEqual(verified['instagram']['channel_id'],'ig')
  for status,time in [('failed',due),('scheduled','2026-12-01T15:01:00Z')]:
   with patch('professional_motion.receipt_verification.query',return_value={'post':{'id':'youtube','status':status,'dueAt':time}}):
    with self.assertRaises(ValueError):verify_scheduled(receipts,mapping,due)
  with patch('professional_motion.receipt_verification.query',side_effect=RuntimeError('credentials expired')):
   with self.assertRaisesRegex(RuntimeError,'expired'):verify_scheduled(receipts,mapping,due)
 def test_submission_without_receipt_blocks_ambiguous_retry(self):
  from scripts import publication_state as state
  with tempfile.TemporaryDirectory() as td,patch.object(state,'ROOT',Path(td)),patch.dict(os.environ,{'PUBLICATION_RECEIPTS_ENABLED':'true','PUBLISH_IMMEDIATE':'true','PRODUCTION_MEDIA_ID':'same-slot','GITHUB_ACTIONS':'false'}):
   state.require_services(['instagram']);state.submission_intent('instagram','ig','2026-12-01T15:00:00Z')
   with self.assertRaisesRegex(RuntimeError,'Reconciliation'):state.submission_intent('instagram','ig','2026-12-01T15:00:00Z')
