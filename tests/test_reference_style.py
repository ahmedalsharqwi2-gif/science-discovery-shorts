import json
import unittest
from pathlib import Path
from professional_motion.merge_chunks import check_styles


class ReferenceStyleTests(unittest.TestCase):
    def test_mixed_review_and_production_cannot_be_joined(self):
        with self.assertRaisesRegex(ValueError, 'mix visual styles'):
            check_styles([{'visual_style':'reference','review':True},
                          {'visual_style':'reference','review':False}])

    def test_mixed_templates_cannot_be_joined(self):
        with self.assertRaises(ValueError):
            check_styles([{'visual_style':'original'}, {'visual_style':'reference'}])

    def test_uniform_review_metadata_survives(self):
        self.assertEqual(check_styles([{'visual_style':'reference','review':True}]*4),
                         ('reference', True))

    def test_existing_chunks_remain_compatible(self):
        self.assertEqual(check_styles([{},{}]), ('original', False))

    def test_empty_partitions_fail(self):
        with self.assertRaises(ValueError):
            check_styles([])

    def test_new_template_is_review_default_and_daily_keeps_approved_style(self):
        workflow=json.loads(Path('.github/workflows/professional-daily.yml').read_text())
        option=workflow['on']['workflow_dispatch']['inputs']['review_style']
        self.assertEqual(option['default'], 'reference')
        render=next(s for s in workflow['jobs']['render']['steps'] if 'REVIEW_VISUAL_STYLE' in s.get('env',{}))
        self.assertIn("needs.produce.outputs.publish == 'true' && 'original'",render['env']['REVIEW_VISUAL_STYLE'])
        # User-controlled workflow_call input travels through a quoted env var.
        self.assertIn('--style "$REVIEW_VISUAL_STYLE"',render['run'])
        self.assertNotIn('${{ inputs.review_style }}',render['run'])


if __name__ == '__main__':
    unittest.main()
