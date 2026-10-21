import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.review_illustration import approved_illustration
from scripts.assemble_video import write_ass_subtitles
from scripts.forced_caption_alignment import validate_events


class ReviewIllustrationTests(unittest.TestCase):
    def test_existing_image_is_bound_to_approved_narration(self):
        root = Path(__file__).resolve().parents[1]
        prepared = json.loads((root / 'review/propeller-gemini-approved.json').read_text())
        image = approved_illustration(prepared)
        self.assertTrue(image['single_topic_image_reused'])
        self.assertFalse(image['new_api_request_used'])
        with self.assertRaisesRegex(RuntimeError, 'another narration'):
            approved_illustration({'narration': 'موضوع مختلف'})

    def test_required_alignment_never_silently_uses_uniform_timing(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {
            'QUALITY_GATES_BLOCKING': 'false', 'CAPTION_ALIGNMENT_REQUIRED': 'true'
        }), patch('scripts.assemble_video.align_words_with_whisper', side_effect=RuntimeError('missing timing')):
            output = Path(folder) / 'captions.ass'
            with self.assertRaisesRegex(RuntimeError, 'missing timing'):
                write_ass_subtitles('ده نص للتجربة', 5, output, audio_path=Path(folder)/'audio.mp3')
            self.assertFalse(output.exists())

    def test_alignment_keeps_rejecting_zero_duration_words(self):
        with self.assertRaisesRegex(RuntimeError, 'Invalid timing at word 0'):
            validate_events([{'text':'ده','start':0,'end':0}], ['ده'], 5)
