import unittest
from datetime import date,datetime,timezone
from unittest.mock import patch
from remotion_factory import health
class AuditTimeOverrides(unittest.TestCase):
 def test_exact_day_uses_owner_approved_time(self):
  policy={'audit_publication_overrides':{'2026-11-04':{'due_at':'2026-11-04T12:45:00Z','approved_by_owner':True}}}
  with patch.object(health,'read_json',return_value=policy):
   self.assertEqual(health.target_due(date(2026,11,4)),datetime(2026,11,4,12,45,tzinfo=timezone.utc))
 def test_other_days_keep_their_schedule(self):
  with patch.object(health,'read_json',return_value={}),patch.object(health,'due_for',return_value='baseline') as due:
   self.assertEqual(health.target_due(date(2026,11,5)),'baseline')
   due.assert_called_once_with(date(2026,11,5))
 def test_cannot_move_audit_to_another_day(self):
  policy={'audit_publication_overrides':{'2026-11-04':{'due_at':'2026-11-05T12:45:00Z','approved_by_owner':True}}}
  with patch.object(health,'read_json',return_value=policy),self.assertRaises(health.AuditFailure):
   health.target_due(date(2026,11,4))
