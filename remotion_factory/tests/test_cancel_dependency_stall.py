import unittest
from datetime import datetime,timezone
from remotion_factory.cancel_dependency_stall import eligible
class DependencyGuard(unittest.TestCase):
 def test_generating_or_paid_job_never_eligible(self):
  for entry in [{'source_run':1,'status':'voice_requested','voice_request_run':1},{'writer_run':1}]:
   job={'run_id':1,'status':'in_progress','steps':[{'name':'Install planning prerequisites','status':'in_progress','started_at':'2026-11-04T20:00:00Z'},{'name':'Freeze original date; verify configured Cairo clock and existing queues','status':'pending'},{'name':'New topic → retained voice → Remotion → full decode → verified configured-time scheduling','status':'pending'}]}
   with self.assertRaises(ValueError):eligible(job,1,{'episodes':{'x':entry}},datetime(2026,11,4,21,tzinfo=timezone.utc))
 def test_only_unwritten_pending_episode_can_be_retained(self):
  job={'run_id':1,'status':'in_progress','steps':[{'name':'Install planning prerequisites','status':'in_progress','started_at':'2026-11-04T20:00:00Z'},{'name':'Freeze original date; verify configured Cairo clock and existing queues','status':'pending'},{'name':'New topic → retained voice → Remotion → full decode → verified configured-time scheduling','status':'pending'}]}
  self.assertTrue(eligible(job,1,{'episodes':{'x':{'source_run':1,'status':'author_pending'}}},datetime(2026,11,4,21,tzinfo=timezone.utc)))
