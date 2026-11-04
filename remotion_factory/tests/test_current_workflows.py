import hashlib,json,re,unittest
from pathlib import Path

class CurrentWorkflowLayout(unittest.TestCase):
 root=Path(__file__).resolve().parents[2]
 def test_only_allowlisted_current_definitions_are_active(self):
  request=json.loads((self.root/'.github/remotion-cleanup-request.json').read_text())
  actual={str(p.relative_to(self.root)) for p in (self.root/'.github/workflows').glob('*') if p.suffix in ('.yml','.yaml')}
  self.assertEqual(actual,set(request['keep_paths']))
  self.assertFalse(actual&set(request['retired_paths']))
 def test_only_production_health_and_read_only_clock_audit_have_schedules(self):
  scheduled=[]
  for p in (self.root/'.github/workflows').glob('*.yml'):
   text=p.read_text()
   try:has_schedule=bool(json.loads(text).get('on',{}).get('schedule'))
   except json.JSONDecodeError:has_schedule=bool(re.search(r'(?m)^\s+schedule\s*:',text))
   if has_schedule:scheduled.append(p.name)
  self.assertEqual(set(scheduled),{'remotion-daily.yml','remotion-health.yml','checks.yml'})
  policy=json.loads((self.root/'config/remotion_daily_release.json').read_text())
  self.assertTrue(policy['enabled']);self.assertEqual((policy['production_local_hour'],policy['publication_local_hour'],policy['publication_day_offset']),(9,17,0))
 def test_consolidated_quality_checks_do_not_have_publication_or_generation_secrets(self):
  text=(self.root/'.github/workflows/checks.yml').read_text()
  workflow=json.loads(text);self.assertEqual(workflow['permissions'],{'contents':'read'})
  self.assertNotIn('secrets.GEMINI',text);self.assertNotIn('secrets.BUFFER',text)
  for name,job in workflow['jobs'].items():
   if name not in ('deploy-independent-clock','clock-access-probe','clock-live-audit'):self.assertNotIn('secrets.',json.dumps(job))
  deploy=workflow['jobs'].get('deploy-independent-clock')
  if deploy:
   self.assertEqual(deploy['if'],"github.ref == 'refs/heads/main' && (github.event_name == 'push' || (github.event_name == 'workflow_dispatch' && inputs.operation == 'deploy-independent-clock'))")
   self.assertEqual(deploy['permissions'],{'contents':'read'})
   self.assertTrue({'independent-clock','remotion'}<=set(deploy['needs']))
   self.assertNotIn('secrets.',json.dumps(deploy['steps'][:3]))
 def test_archived_contract_fixtures_match_original_git_blob_hashes(self):
  report=json.loads((self.root/'reviews/cleanup/workflow-simplification.json').read_text())
  expected={Path(item['path']).name:item['sha'] for item in report['removed']}
  for p in (self.root/'tests/fixtures/retired_workflows').glob('*.yml'):
   data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
   self.assertEqual(blob,expected[p.name])

 def test_cloudflare_access_probe_is_read_only_and_explicit(self):
  workflow=json.loads((self.root/'.github/workflows/checks.yml').read_text())
  probe=workflow['jobs']['clock-access-probe']
  self.assertEqual(probe['if'],"github.event_name == 'push' && github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[probe-cloudflare-access]')")
  self.assertEqual(probe['permissions'],{'contents':'read'})
  command=next(step for step in probe['steps'] if step.get('run'))['run']
  self.assertEqual(command,'node --use-env-proxy probe-access.mjs')

 def test_custom_github_secret_uses_a_non_reserved_name(self):
  text=(self.root/'.github/workflows/checks.yml').read_text()
  self.assertNotIn('secrets.GITHUB_DISPATCH_TOKEN',text)
  self.assertIn('secrets.FACTORY_DISPATCH_TOKEN',text)

 def test_periodic_clock_audit_cannot_run_generation_or_deploy_jobs(self):
  workflow=json.loads((self.root/'.github/workflows/checks.yml').read_text())
  for name in ('test','image_fallback','motion-kit-tests','scene_director','validation','remotion','independent-clock'):
   self.assertIn("github.event_name != 'schedule'",workflow['jobs'][name]['if'])
  self.assertNotIn("github.event_name == 'schedule'",workflow['jobs']['deploy-independent-clock']['if'])
  audit=workflow['jobs']['clock-live-audit']
  self.assertEqual(audit['permissions'],{'contents':'read','issues':'write'})
  self.assertNotIn('FACTORY_DISPATCH_TOKEN',json.dumps(audit))
  self.assertNotIn('GEMINI',json.dumps(audit));self.assertNotIn('BUFFER',json.dumps(audit))
  self.assertEqual(workflow['on']['schedule'],[{'cron':'*/15 * * * *'}])
