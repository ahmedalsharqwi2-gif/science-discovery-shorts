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
 def test_retry_revises_same_reserved_topic_once_after_measured_duration_failure(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'registry.json';old={'topic_key':'same','title':'same','visual_family':'field','variant':'magnet','source':{'url':'https://science.nasa.gov/earth/earths-magnetosphere/','publisher':'NASA'}}
   state.write_text(json.dumps({'episodes':[{'slot':'today','status':'reserved','story':old,'needs_narration_revision':True,'narration_feedback':{'measured_seconds':106,'target_seconds':150}}]}))
   revised={**old,'title':'same expanded'}
   with patch.object(editorial,'ROOT',root),patch.object(editorial,'STATE',state),patch.object(editorial,'write_sourced',return_value=revised) as write:
    self.assertEqual(editorial.prepare('science','today')['topic_key'],'same');self.assertEqual(write.call_count,1)
    data=json.loads(state.read_text());self.assertEqual(len(data['episodes']),1);self.assertEqual(data['episodes'][0]['narration_revision_attempts'],1)
    data['episodes'][0]['needs_narration_revision']=True;state.write_text(json.dumps(data))
    with self.assertRaisesRegex(RuntimeError,'manual review'):editorial.prepare('science','today')
 def test_opening_proper_name_does_not_hide_real_measured_phrase_anchors(self):
  from professional_motion.alignment import measured_timing
  words=['أوبن','إيه','آي','أعلنت','تحديث']+['كلمة'+str(i) for i in range(60)]
  story={'scenes':[{'narration':' '.join(words)}]}
  actual=[{'text':w,'start':i*.4,'end':i*.4+.2} for i,w in enumerate(words) if i>=5]
  result=measured_timing(story,40,[('test',actual)])
  self.assertGreaterEqual(result['coverage'],.85);self.assertEqual(result['scenes'][0]['start'],0)
 def test_existing_release_asset_with_other_bytes_is_never_reused(self):
  from film_factory.buffer import ContentPublisher
  from unittest.mock import Mock
  with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'GITHUB_TOKEN':'test','GITHUB_REPOSITORY':'owner/repo','PRODUCTION_MEDIA_ID':'same-day'},clear=True):
   movie=Path(td)/'new.mp4';movie.write_bytes(b'new current film')
   response=Mock(status_code=200);response.json.return_value={'assets':[{'name':'science-video-same-day.mp4','browser_download_url':'https://example.test/old.mp4','digest':'sha256:'+'0'*64}]}
   with patch('film_factory.buffer.requests.get',return_value=response),patch('film_factory.buffer.requests.post') as post:
    with self.assertRaisesRegex(RuntimeError,'checksum'):ContentPublisher()._release_asset_url(movie)
    post.assert_not_called()
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
 def test_iso_due_survives_workflow_output_and_legacy_lowercase_is_accepted(self):
  from scripts.daily_schedule import validate_slot
  from professional_motion import cli
  import sys
  with tempfile.TemporaryDirectory() as td:
   out=Path(td)/'outputs'
   result={'run':True,'publish':True,'reason':'eligible','due':'2026-12-01T15:00:00Z'}
   with patch.object(sys,'argv',['cli','decision','science','--mode','daily']),patch.object(cli,'decision',return_value=result),patch.dict(os.environ,{'GITHUB_OUTPUT':str(out),'GITHUB_REF_NAME':'main'},clear=False):cli.main()
   self.assertIn('due=2026-12-01T15:00:00Z',out.read_text());self.assertIn('run=true',out.read_text())
  self.assertEqual(validate_slot('2026-12-01t15:00:00z',datetime(2026,12,1,10,tzinfo=timezone.utc)).hour,15)
 def test_submission_without_receipt_blocks_ambiguous_retry(self):
  from scripts import publication_state as state
  with tempfile.TemporaryDirectory() as td,patch.object(state,'ROOT',Path(td)),patch.dict(os.environ,{'PUBLICATION_RECEIPTS_ENABLED':'true','PUBLISH_IMMEDIATE':'true','PRODUCTION_MEDIA_ID':'same-slot','GITHUB_ACTIONS':'false'}):
   state.require_services(['instagram']);state.submission_intent('instagram','ig','2026-12-01T15:00:00Z')
   with self.assertRaisesRegex(RuntimeError,'Reconciliation'):state.submission_intent('instagram','ig','2026-12-01T15:00:00Z')
