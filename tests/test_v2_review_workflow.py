"""Archived recovery contracts; active workflow layout is tested separately."""
import json
from pathlib import Path
import unittest

class CandidateWorkflowTests(unittest.TestCase):
    def test_candidate_has_no_automatic_trigger_or_publishing_secret(self):
        workflow=json.loads(Path('tests/fixtures/retired_workflows/production-v2-review.yml').read_text())
        self.assertEqual(set(workflow['on']),{'workflow_dispatch'})
        self.assertFalse(workflow['concurrency']['cancel-in-progress'])
        text=json.dumps(workflow)
        self.assertNotIn('BUFFER_API_KEY',text)
        self.assertNotIn('professional_motion.cli publish',text)
        self.assertIn('production_v2.review',text)
        self.assertEqual(workflow['permissions'],{'contents':'read'})
    def test_candidate_cannot_accidentally_activate_legacy_replacement(self):
        config=json.loads(Path('config/production_v2.json').read_text())
        self.assertEqual(config['active_pipeline'],'legacy')
        self.assertFalse(config['automatic_cutover'])
        self.assertEqual(len(config['acceptance_profiles']),5)

if __name__=='__main__':unittest.main()

class ExistingDispatcherTests(unittest.TestCase):
    def test_default_dispatch_preserves_legacy_and_v2_is_explicit(self):
        import yaml
        dispatch=yaml.safe_load(Path('tests/fixtures/retired_workflows/professional-daily.yml').read_text())
        self.assertEqual(dispatch['on']['workflow_dispatch']['inputs']['pipeline']['default'],'legacy')
        self.assertEqual(dispatch['on']['workflow_call']['inputs']['pipeline']['default'],'legacy')
        self.assertEqual(dispatch['jobs']['produce']['if'],"${{ inputs.pipeline != 'v2' }}")
        self.assertEqual(dispatch['jobs']['v2-candidate-review']['if'],"${{ inputs.pipeline == 'v2' }}")
        self.assertTrue(dispatch['jobs']['v2-candidate-review']['with']['caller_serialized'])
        self.assertIn("inputs.pipeline != 'v2'",dispatch['jobs']['failure-alert']['if'])
        candidate=json.loads(Path('tests/fixtures/retired_workflows/production-v2-generate.yml').read_text())
        self.assertNotIn('schedule',candidate['on'])
        self.assertIn("format('v2-child-{0}'",candidate['concurrency']['group'])
        self.assertEqual(candidate['jobs']['candidate']['env']['GEMINI_API_KEY'],'${{ secrets.GEMINI_API_KEY }}')
        self.assertNotIn('BUFFER_API_KEY',json.dumps(candidate))
    def test_legacy_behavior_is_archived_and_only_its_clock_is_retired(self):
        import yaml
        baseline=yaml.safe_load(Path('reviews/factory-legacy-workflow-before-cutover.yml').read_text())
        current=yaml.safe_load(Path('tests/fixtures/retired_workflows/professional-daily.yml').read_text())
        baseline['on'].pop('schedule',None);current['on'].pop('schedule',None)
        self.assertEqual(current,baseline)
