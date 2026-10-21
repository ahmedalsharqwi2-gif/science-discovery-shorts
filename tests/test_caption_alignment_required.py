import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.assemble_video import write_ass_subtitles
from scripts.forced_caption_alignment import validate_events


class CaptionAlignmentRequiredTests(unittest.TestCase):
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
