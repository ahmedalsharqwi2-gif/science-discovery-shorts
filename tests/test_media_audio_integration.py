import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from scripts.media_audio import ducking_filters, normalized_audio_args


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg required")
class RealAudioIntegrationTests(unittest.TestCase):
    def test_real_ducking_graph_has_valid_split_and_audible_original(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "mixed.wav"
            filters = ducking_filters("[0:a]", "[1:a]")
            filters.append("[voice][ducked]amix=inputs=2:duration=first:normalize=0[a]")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
                            "-f", "lavfi", "-i", "sine=frequency=700:sample_rate=48000", "-t", "0.5",
                            "-filter_complex", ";".join(filters), "-map", "[a]", str(out)], check=True)
            result = subprocess.run(["ffmpeg", "-v", "info", "-i", str(out), "-af", "volumedetect", "-f", "null", "-"],
                                    capture_output=True, text=True, check=True)
            self.assertNotIn("mean_volume: -91.0", result.stderr)
            self.assertRegex(result.stderr, r"mean_volume: -[23]\d\.")

    def test_muted_normalization_produces_audio_even_with_silent_video(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            dest = Path(temp) / "normalized.mp4"
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=s=64x64:d=0.3", "-an", str(source)], check=True)
            extra, mapping = normalized_audio_args(source, False)
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source), *extra, "-t", "0.3",
                            "-map", "0:v:0", *mapping, "-c:v", "copy", str(dest)], check=True)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(dest)], capture_output=True, text=True, check=True)
            audio = [s for s in json.loads(probe.stdout)["streams"] if s["codec_type"] == "audio"]
            self.assertEqual(len(audio), 1)
            self.assertEqual(audio[0]["sample_rate"], "48000")
            self.assertEqual(audio[0]["channels"], 2)
