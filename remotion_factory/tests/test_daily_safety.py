import unittest
from datetime import datetime,timezone
from unittest.mock import patch
from remotion_factory.daily import slot_for
from remotion_factory.publish import submit_one
class CivilTime(unittest.TestCase):
 def test_winter_previous_day19(self):
  now=datetime(2026,12,14,17,tzinfo=timezone.utc)
  self.assertEqual(slot_for(now,'schedule','0 17 * * *',now=now).isoformat(),'2026-12-15T10:00:00+00:00')
 def test_summer_and_second_cron_skip(self):
  now=datetime(2027,7,14,16,tzinfo=timezone.utc)
  self.assertEqual(slot_for(now,'schedule','0 16 * * *',now=now).hour,9)
  self.assertIsNone(slot_for(now,'schedule','0 17 * * *',now=now))
 def test_expired_rerun_does_not_advance(self):
  with self.assertRaisesRegex(ValueError,'expired'):slot_for(datetime(2026,12,14,17,tzinfo=timezone.utc),'workflow_dispatch',now=datetime(2026,12,16,7,tzinfo=timezone.utc))
 def test_delayed_wrong_day_or_wrong_hour_skip(self):
  now=datetime(2026,12,14,17,tzinfo=timezone.utc)
  self.assertIsNone(slot_for(now,'schedule','0 16 * * *',now=now))
class Submission(unittest.TestCase):
 @patch('remotion_factory.publish.query')
 @patch('remotion_factory.publish.queued',return_value=[])
 def test_uncertain_send_never_repeated(self,queue,query):
  with self.assertRaisesRegex(ValueError,'unacknowledged'):submit_one('youtube',{'channel':'c'},'2026-11-04T15:00:00Z','https://example.org/v.mp4','title','caption',{'phase':'uncertain'},lambda:None)
  query.assert_not_called()
 @patch('remotion_factory.publish.query')
 @patch('remotion_factory.publish.queued',return_value=[{'id':'another','channelId':'c','status':'scheduled','dueAt':'2026-11-04T15:00:00Z','assets':[{'source':'https://example.org/another.mp4'}]}])
 def test_existing_other_post_never_replaced(self,queue,query):
  with self.assertRaisesRegex(ValueError,'occupies'):submit_one('youtube',{'channel':'c'},'2026-11-04T15:00:00Z','https://example.org/v.mp4','title','caption',{},lambda:None)
  query.assert_not_called()
if __name__=='__main__':unittest.main()
