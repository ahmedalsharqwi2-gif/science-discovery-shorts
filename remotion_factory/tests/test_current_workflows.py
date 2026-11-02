import hashlib,json,re,unittest
from pathlib import Path

class CurrentWorkflowLayout(unittest.TestCase):
 root=Path(__file__).resolve().parents[2]
 def test_only_allowlisted_current_definitions_are_active(self):
  request=json.loads((self.root/'.github/remotion-cleanup-request.json').read_text())
  actual={str(p.relative_to(self.root)) for p in (self.root/'.github/workflows').glob('*') if p.suffix in ('.yml','.yaml')}
  self.assertEqual(actual,set(request['keep_paths']))
  self.assertFalse(actual&set(request['retired_paths']))
 def test_only_factory_and_health_have_schedules(self):
  scheduled=[]
  for p in (self.root/'.github/workflows').glob('*.yml'):
   text=p.read_text()
   try:has_schedule=bool(json.loads(text).get('on',{}).get('schedule'))
   except json.JSONDecodeError:has_schedule=bool(re.search(r'(?m)^\s+schedule\s*:',text))
   if has_schedule:scheduled.append(p.name)
  self.assertEqual(set(scheduled),{'remotion-daily.yml','remotion-health.yml'})
  policy=json.loads((self.root/'config/remotion_daily_release.json').read_text())
  self.assertTrue(policy['enabled']);self.assertEqual((policy['production_local_hour'],policy['publication_local_hour'],policy['publication_day_offset']),(9,17,0))
 def test_consolidated_quality_checks_do_not_have_publication_or_generation_secrets(self):
  text=(self.root/'.github/workflows/checks.yml').read_text()
  self.assertNotIn('secrets.',text);self.assertEqual(json.loads(text)['permissions'],{'contents':'read'})
 def test_archived_contract_fixtures_match_original_git_blob_hashes(self):
  report=json.loads((self.root/'reviews/cleanup/workflow-simplification.json').read_text())
  expected={Path(item['path']).name:item['sha'] for item in report['removed']}
  for p in (self.root/'tests/fixtures/retired_workflows').glob('*.yml'):
   data=p.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
   self.assertEqual(blob,expected[p.name])
