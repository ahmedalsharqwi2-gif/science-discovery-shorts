import json
import shutil
import subprocess
import unittest
from pathlib import Path

@unittest.skipUnless(shutil.which("ffprobe"), "FFprobe required")
class StoredMusicAssetsTests(unittest.TestCase):
    def test_every_stored_track_is_decodable_audio_with_useful_duration(self):
        directory = Path(__file__).resolve().parents[1] / "assets/music"
        tracks = sorted(p for p in directory.iterdir() if p.suffix.lower() in {".mp3", ".wav"})
        self.assertGreaterEqual(len(tracks), 5)
        for track in tracks:
            with self.subTest(track=track.name):
                probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                    "format=duration:stream=codec_type", "-of", "json", str(track)],
                    capture_output=True, text=True, check=True)
                result = json.loads(probe.stdout)
                self.assertTrue(any(s.get("codec_type") == "audio" for s in result["streams"]))
                self.assertGreater(float(result["format"]["duration"]), 10)
