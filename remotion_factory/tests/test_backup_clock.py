import unittest
from datetime import datetime,timezone
from remotion_factory.daily import slot_for
class BackupClock(unittest.TestCase):
 def test_winter_backup_preserves_noon_slot(self):
  t=datetime(2030,1,2,17,17,tzinfo=timezone.utc)
  self.assertEqual(slot_for(t,'schedule','17 17 * * *',now=t),datetime(2030,1,3,10,tzinfo=timezone.utc))
 def test_summer_backup_preserves_noon_slot(self):
  t=datetime(2030,7,2,16,17,tzinfo=timezone.utc)
  self.assertEqual(slot_for(t,'schedule','17 16 * * *',now=t),datetime(2030,7,3,9,tzinfo=timezone.utc))
 def test_wrong_dst_is_a_noop(self):
  t=datetime(2030,1,2,17,17,tzinfo=timezone.utc)
  self.assertIsNone(slot_for(t,'schedule','17 16 * * *',now=t))
 def test_expired_backup_never_rolls_over(self):
  t=datetime(2030,1,2,17,17,tzinfo=timezone.utc)
  with self.assertRaises(ValueError):slot_for(t,'schedule','17 17 * * *',now=datetime(2030,1,3,16,tzinfo=timezone.utc))
