import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.audio_duration import fit_narration


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg required")
class AudioDurationTests(unittest.TestCase):
    def make_audio(self, path, duration):
        subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i",
                        f"sine=frequency=440:duration={duration}", str(path)],
                       check=True, capture_output=True)

    def test_retimes_full_audio_into_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.wav"
            self.make_audio(path, 10)
            actual = fit_narration(path, 7, 9, 8.5)
            self.assertTrue(7 <= actual <= 9)
            self.assertAlmostEqual(actual, 8, delta=0.1)

    def test_large_pace_change_refused_without_replacing_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.wav"
            self.make_audio(path, 20)
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                fit_narration(path, 7, 9, 8)
            self.assertEqual(path.read_bytes(), original)

    def test_longer_feasible_target_avoids_unnecessary_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "voice.wav"
            self.make_audio(path, 10.699)
            actual = fit_narration(path, 6, 8.9, 8.5)
            self.assertTrue(6 <= actual <= 8.9)
            self.assertAlmostEqual(actual, 10.699 / 1.25, delta=0.1)
