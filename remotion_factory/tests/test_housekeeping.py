import unittest
from remotion_factory.housekeeping import category,disposable
class CleanupGuards(unittest.TestCase):
 def test_defaults_recovery_refs_and_protected_branches_never_deleted(self):
  for name,protected in [('main',False),('codex/rebuild-production-v2',False),('codex/production-v2-state',False),('codex/production-v2-diagnostics',False),('fix/important',True)]:self.assertTrue(category(name,protected,'main','',set(),set()).startswith('keep_'))
 def test_open_pr_active_run_and_workflow_refs_are_preserved(self):
  name='codex/professional-review-run-12345678'
  for workflows,prs,runs in [(name,set(),set()),('',{name},set()),('',set(),{name})]:self.assertTrue(category(name,False,'main',workflows,prs,runs).startswith('keep_'))
 def test_snapshot_is_a_candidate_not_an_automatic_delete(self):self.assertEqual(category('codex/professional-review-run-12345678',False,'main','',set(),set()),'snapshot')
 def test_unique_feature_work_requires_merged_proof(self):self.assertEqual(category('feat/new-engine',False,'main','',set(),set()),'check_merged')
 def test_only_generated_tracked_paths_are_removable(self):
  for path in ['engine/__pycache__/render.cpython-311.pyc','.pytest_cache/v/cache','folder/.DS_Store']:self.assertTrue(disposable(path))
  for path in ['state/receipts.json','reviews/sample.mp4','.voice_cache/original.wav','production_v2/render.py','remotion_motion/package-lock.json','.github/workflows/remotion-daily.yml','state/__pycache__/keep.pyc']:self.assertFalse(disposable(path))
if __name__=='__main__':unittest.main()
