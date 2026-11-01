import importlib.util
import unittest
from datetime import datetime
from production_v2.schedule import window,require_future_due

class PreviousDayScheduleTests(unittest.TestCase):
 def test_winter_preparation_targets_next_day_at_five(self):
  result=window(datetime.fromisoformat('2026-11-02T07:00:00+00:00'))
  self.assertTrue(result['run']);self.assertEqual(result['slot'],'daily-2026-11-03')
  self.assertEqual(result['preparation_date'],'2026-11-02')
  self.assertEqual(result['due_at'],'2026-11-03T15:00:00Z')
 def test_summer_preparation_targets_next_day_at_five(self):
  result=window(datetime.fromisoformat('2026-07-01T06:00:00+00:00'))
  self.assertEqual(result['due_at'],'2026-07-02T14:00:00Z')
 def test_due_uses_publication_day_daylight_saving_offset(self):
  result=window(datetime.fromisoformat('2026-04-23T07:00:00+00:00'))
  self.assertEqual(result['due_at'],'2026-04-24T14:00:00Z')
 def test_retry_keeps_original_target_and_never_rolls_a_missed_date(self):
  initial=window(datetime.fromisoformat('2026-11-02T07:00:00+00:00'))
  retry=window(datetime.fromisoformat('2026-11-03T08:00:00+00:00'),initial['publication_date'])
  self.assertTrue(retry['run']);self.assertEqual(retry['due_at'],initial['due_at'])
  late=window(datetime.fromisoformat('2026-11-03T15:01:00+00:00'),initial['publication_date'])
  self.assertFalse(late['run']);self.assertEqual(late['reason'],'missed')
  self.assertEqual(late['due_at'],initial['due_at'])
 def test_accepted_next_day_due_and_rejected_past_due(self):
  due='2026-11-03T15:00:00Z'
  require_future_due(due,datetime.fromisoformat('2026-11-02T10:00:00+00:00'))
  with self.assertRaises(ValueError):require_future_due(due,datetime.fromisoformat('2026-11-03T15:00:01+00:00'))
 def test_preparation_does_not_start_before_nine_cairo(self):
  self.assertEqual(window(datetime.fromisoformat('2026-11-02T06:59:59+00:00'))['reason'],'too_early')
if __name__=='__main__':unittest.main()
