import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from film_factory.metadata import create
from film_factory.motion import events
from film_factory.publish import channels
from film_factory.topics import NYOS,select
from scripts.daily_schedule import next_slot,validate_slot
from scripts import publication_state

class DailyCinemaTests(unittest.TestCase):
 def setUp(self):
  self.old=Path.cwd();self.temp=tempfile.TemporaryDirectory();os.chdir(self.temp.name)
 def tearDown(self):os.chdir(self.old);self.temp.cleanup()
 def plan(self):return {'title':'ليه رواد الفضاء بيطفوا؟','source':{'url':'https://www.nasa.gov/example','publisher':'NASA'},'scenes':[{'labels':['رواد الفضاء','الجاذبية']}],'editorial_review':{'supported':True},'fiction':False,'documented':True}
 def test_fiction_is_never_mislabeled_as_true_horror(self):
  p=self.plan();p['fiction']=True
  with self.assertRaisesRegex(ValueError,'Fiction'):create(p,'horror')
 def test_title_and_hashtags_follow_the_actual_topic(self):
  m=create(self.plan(),'science');self.assertTrue(m['title'].startswith('اسرار الكون |'));self.assertIn('#الجاذبية',m['hashtags']);self.assertIn('https://www.nasa.gov/example',m['caption']);self.assertLessEqual(len(m['title']),100)
 def test_unreviewed_script_cannot_publish(self):
  p=self.plan();p['editorial_review']['supported']=False
  with self.assertRaisesRegex(ValueError,'review'):create(p,'science')
 def test_summer_and_winter_both_target_five_in_cairo(self):
  summer=next_slot(datetime(2026,7,1,8,tzinfo=timezone.utc));winter=next_slot(datetime(2026,12,1,8,tzinfo=timezone.utc))
  self.assertEqual(summer.hour,14);self.assertEqual(winter.hour,15)
 def test_late_publication_never_falls_back_to_immediate(self):
  with self.assertRaisesRegex(ValueError,'passed'):validate_slot('2026-07-01T14:00:00Z',datetime(2026,7,1,15,tzinfo=timezone.utc))
 def test_documented_horror_has_no_supernatural_ending(self):
  with patch('film_factory.topics.candidates',return_value=[NYOS]):
   brief=select('horror',lambda *a,**k:self.fail('Known reviewed capsule needs no extraction'))
   self.assertTrue(brief['documented']);self.assertIn('1986',brief['era']);self.assertTrue(brief['source']['url'].startswith('https://'))
 def test_effect_follows_spoken_subject_and_not_a_generic_scene_time(self):
  cues=events([{'text':'الموج','start':18.4},{'text':'منارة','start':22.2}], 'horror')
  self.assertEqual([(x['kind'],x['at']) for x in cues],[('waves',18.4),('lamp',22.2)])
 def test_news_channel_selection_never_uses_an_unrelated_page(self):
  replies=[{'account':{'organizations':[{'id':'org'}]}},{'channels':[{'id':'science','name':'اسرار الكون','displayName':'اسرار الكون','service':'facebook','isQueuePaused':False}]}]
  with patch.dict(os.environ,{},clear=True),patch('film_factory.publish.query',side_effect=replies):
   with self.assertRaisesRegex(ValueError,'No uniquely matching'):channels('news')
 def test_receipt_survives_partial_publication_and_can_be_reused(self):
  with patch.object(publication_state,'ROOT',Path.cwd()),patch.dict(os.environ,{'PUBLICATION_RECEIPTS_ENABLED':'true','PUBLISH_IMMEDIATE':'true','PRODUCTION_MEDIA_ID':'first-sample','BUFFER_OUTCOME':'success'},clear=True):
   publication_state.require_services({'facebook','youtube'});publication_state.record_receipt('facebook','real-provider-id')
   self.assertEqual(publication_state.accepted_receipt('facebook')['id'],'real-provider-id');self.assertIsNone(publication_state.accepted_receipt('youtube'))
   with self.assertRaisesRegex(RuntimeError,'Missing'):publication_state.confirm_stock()
if __name__=='__main__':unittest.main()
