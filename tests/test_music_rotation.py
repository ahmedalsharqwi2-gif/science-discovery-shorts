import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.media_audio import add_topic_soundtrack
from scripts.music_rotation import select_track

CHANNEL = "science"
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class MusicRotationTests(unittest.TestCase):
    def test_run_id_rotates_only_background_music_not_sfx(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "assets" / "music"
            sfx = root / "assets" / "sfx"
            music.mkdir(parents=True)
            sfx.mkdir(parents=True)
            for name in ("01-first.mp3", "02-second.mp3", "03-third.mp3"):
                (music / name).write_bytes(b"music placeholder")
            (sfx / "00-impact.mp3").write_bytes(b"sfx placeholder")

            with patch.dict(os.environ, {"GITHUB_RUN_ID": "0"}, clear=True):
                first = select_track(root, CHANNEL)
            with patch.dict(os.environ, {"GITHUB_RUN_ID": "1"}, clear=True):
                second = select_track(root, CHANNEL)

            self.assertNotEqual(first, second)
            self.assertEqual(first.parent, music)
            self.assertEqual(second.parent, music)
            self.assertNotEqual(first.parent, sfx)

    def test_rotated_music_mix_muxes_to_video_with_matching_duration(self):
        duration = 2.4
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            base_audio = temp / "base.mp3"
            narration = temp / "narration.mp3"
            source_video = temp / "source.mp4"
            final_video = temp / "final.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            "anullsrc=r=48000:cl=stereo", "-t", "3", "-c:a", "libmp3lame", str(base_audio)], check=True)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            "sine=frequency=700:sample_rate=48000", "-t", "3", "-c:a", "libmp3lame", str(narration)], check=True)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                            "color=c=blue:s=160x284:r=24:d=3", "-an", "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", str(source_video)], check=True)

            with patch.dict(os.environ, {
                "BACKGROUND_MUSIC_ENABLED": "true",
                "BACKGROUND_MUSIC_VOLUME": "0.06",
                "GITHUB_RUN_ID": "1",
            }, clear=True):
                add_topic_soundtrack(base_audio, narration, duration, CHANNEL)

            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source_video), "-i", str(base_audio),
                            "-map", "0:v:0", "-map", "1:a:0", "-t", str(duration), "-c:v", "copy",
                            "-c:a", "aac", str(final_video)], check=True)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                    "format=duration:stream=codec_type,duration", "-of", "json", str(final_video)],
                                   capture_output=True, text=True, check=True)
            result = json.loads(probe.stdout)
            streams = {stream["codec_type"]: float(stream["duration"]) for stream in result["streams"]}
            self.assertIn("video", streams)
            self.assertIn("audio", streams)
            self.assertLessEqual(abs(streams["video"] - streams["audio"]), 0.12)
            self.assertLessEqual(abs(float(result["format"]["duration"]) - duration), 0.15)


if __name__ == "__main__":
    unittest.main()
