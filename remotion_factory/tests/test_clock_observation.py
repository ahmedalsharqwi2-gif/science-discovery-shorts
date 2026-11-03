import unittest
from datetime import date
from remotion_factory.health import clock_source

class ClockProvenance(unittest.TestCase):
 day=date(2030,1,3)
 def run_record(self,**changes):return {'status':'completed','conclusion':'success','event':'workflow_dispatch','created_at':'2030-01-03T07:00:10Z',**changes}
 def decision(self,**changes):return {'run':True,'due_at':'2030-01-03T15:00:00Z','reason':'eligible','trigger_source':'cloudflare-clock','dry_run':False,**changes}
 def test_independent_clock_has_explicit_provenance(self):self.assertEqual(clock_source(self.run_record(),self.decision(),self.day),'cloudflare-clock')
 def test_github_schedule_stays_distinct(self):self.assertEqual(clock_source(self.run_record(event='schedule'),self.decision(trigger_source='schedule'),self.day),'github-schedule')
 def test_dry_runs_and_tests_cannot_fake_clock_success(self):
  for decision in (self.decision(dry_run=True),self.decision(trigger_source='cloudflare-clock-test'),self.decision(dry_run=None)):
   self.assertIsNone(clock_source(self.run_record(),decision,self.day))
 def test_manual_recovery_cannot_fake_automatic_clock(self):
  self.assertIsNone(clock_source(self.run_record(event='push'),self.decision(),self.day))
  self.assertIsNone(clock_source(self.run_record(),self.decision(trigger_source='manual'),self.day))
  self.assertIsNone(clock_source(self.run_record(created_at='2030-01-03T09:32:00Z'),self.decision(),self.day))
 def test_wrong_day_or_target_or_dst_noop_never_passes(self):
  self.assertIsNone(clock_source(self.run_record(created_at='2030-01-02T07:00:00Z'),self.decision(),self.day))
  self.assertIsNone(clock_source(self.run_record(),self.decision(due_at='2030-01-04T15:00:00Z'),self.day))
  self.assertIsNone(clock_source(self.run_record(event='schedule'),self.decision(reason='other DST trigger'),self.day))
 def test_failed_or_in_progress_is_not_success(self):
  self.assertIsNone(clock_source(self.run_record(conclusion='failure'),self.decision(),self.day))
  self.assertIsNone(clock_source(self.run_record(status='in_progress'),self.decision(),self.day))

class ClockSchedulerDiscovery(unittest.TestCase):
 def test_independent_dispatch_is_found_without_pretending_it_is_github_cron(self):
  import json
  from unittest.mock import patch
  from remotion_factory.health import scheduler
  run={'id':123,'html_url':'https://github.com/owner/repo/actions/runs/123','status':'completed','conclusion':'success','event':'workflow_dispatch','created_at':'2030-01-03T07:01:00Z'}
  decision={'run':False,'reason':'all three existing destination slots occupied; preserve them','due_at':'2030-01-03T15:00:00Z','trigger_source':'cloudflare-clock','dry_run':False}
  with patch('remotion_factory.health.gh',side_effect=[{'workflow_runs':[run]},{'jobs':[{'id':8,'started_at':'2030-01-03T07:01:10Z'}]},'2030-01-03T07:01:12Z '+json.dumps(decision)]) as api:
   result=scheduler(date(2030,1,3));self.assertEqual(result['clock_source'],'cloudflare-clock');self.assertEqual(result['event'],'workflow_dispatch');self.assertEqual(result['run_id'],123)
   self.assertNotIn('event=schedule',api.call_args_list[0].args[0])
 def test_a_successful_integration_test_is_not_an_observed_production_clock(self):
  import json
  from unittest.mock import patch
  from remotion_factory.health import scheduler,AuditFailure
  run={'id':123,'html_url':'https://github.com/owner/repo/actions/runs/123','status':'completed','conclusion':'success','event':'workflow_dispatch','created_at':'2030-01-03T07:01:00Z'}
  decision={'run':False,'reason':'dry run; no provider mutation','due_at':'2030-01-03T15:00:00Z','trigger_source':'cloudflare-clock-test','dry_run':True}
  with patch('remotion_factory.health.gh',side_effect=[{'workflow_runs':[run]},{'jobs':[{'id':8}]},json.dumps(decision)]):
   with self.assertRaises(AuditFailure):scheduler(date(2030,1,3))
