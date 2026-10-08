import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.audio_duration import fit_narration
from scripts.generate_content import normalize_narration_response


class DurationRecoveryTests(unittest.TestCase):
    def test_plain_escaped_unicode_is_decoded_before_tts(self):
        self.assertEqual(normalize_narration_response(r'نص \u0645\u0634\u0643\u0648\u0644.'), 'نص مشكول.')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_38_second_audio_gets_bounded_slowdown_and_tiny_closing_pause(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'voice.wav'
            subprocess.run(['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=38.21', str(path)], check=True)
            duration = fit_narration(path, 45, 59, 55)
            self.assertGreaterEqual(duration, 45)
            self.assertLessEqual(duration, 46)

    def test_very_short_audio_still_requires_regeneration(self):
        with patch('scripts.audio_duration.probe_duration', return_value=25):
            with self.assertRaises(ValueError):
                fit_narration(Path('voice.wav'), 45, 59, 55)


if __name__ == '__main__':
    unittest.main()
