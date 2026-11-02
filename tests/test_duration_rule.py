import unittest
from professional_motion.duration_rules import require_duration
class PermanentDurationRules(unittest.TestCase):
 def test_news_is_strictly_over_sixty(self):
  self.assertEqual(require_duration(66.5,'news'),66.5)
  for n in (0,60,180,float('nan'),float('inf')):
   with self.assertRaises(ValueError):require_duration(n,'news')
 def test_other_channels_are_strictly_over_ninety(self):
  for profile in ('science','horror','history','stickman'):
   for n in (60,89.99,90,180,float('nan')):
    with self.assertRaises(ValueError):require_duration(n,profile)
   for n in (90.001,108.57,119.56,155.32):
    self.assertEqual(require_duration(n,profile),n)
 def test_unknown_channel_is_not_silently_accepted(self):
  with self.assertRaises(ValueError):require_duration(120,'unknown')
