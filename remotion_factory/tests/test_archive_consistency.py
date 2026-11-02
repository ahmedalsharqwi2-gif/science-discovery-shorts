import unittest
from unittest.mock import patch
from remotion_factory.housekeeping import archive,AuditFailure

class ArchiveConsistency(unittest.TestCase):
 def test_delayed_ref_visibility_is_rechecked_before_acceptance(self):
  expected={'object':{'sha':'original'}}
  with patch('remotion_factory.housekeeping.gh',side_effect=[None,{},None,None,expected]) as api,patch('remotion_factory.housekeeping.time.sleep'):
   self.assertEqual(archive('archive/test','original'),'archive/test')
   self.assertEqual(sum(c.args[1:2]==('POST',) for c in api.call_args_list),1)
 def test_wrong_archive_never_authorizes_deletion(self):
  with patch('remotion_factory.housekeeping.gh',return_value={'object':{'sha':'different'}}):
   with self.assertRaises(AuditFailure):archive('archive/test','original')
 def test_missing_archive_stops_after_bounded_reads(self):
  with patch('remotion_factory.housekeeping.gh',return_value=None),patch('remotion_factory.housekeeping.time.sleep'):
   with self.assertRaises(AuditFailure):archive('archive/test','original')
