"""Pre-publish source-diversity checks for cinematic science videos."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import broll_quality_pipeline as gate


class BrollSourceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.video = self.root / "final.mp4"
        self.video.write_bytes(b"fixture-video")
        self.addCleanup(self.temp.cleanup)

    def evaluate_manifest(self, entries):
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps(entries), encoding="utf-8")
        with patch.object(gate, "probe_video", return_value={
            "width": 1080, "height": 1920, "duration_seconds": 48.0,
        }), patch.object(gate, "detect_black_intervals", return_value=[]):
            return gate.evaluate(
                self.video, manifest, None, self.root / "state/montage_quality.json",
                "vertical", 4, 0.30, min_external_sources=6, min_external_share=0.65,
            )

    def make_entries(self, external_count):
        entries = []
        for index in range(8):
            clip = self.root / f"scene-{index}.mp4"
            clip.write_bytes(b"scene")
            if index < external_count:
                entries.append({
                    "file": str(clip),
                    "source": "pexels_photo",
                    "source_url": f"https://www.pexels.com/photo/science-{index}/",
                    "license": "Pexels",
                    "media_type": "photo",
                    "asset_id": f"pexels-photo-{index}",
                    "pexels_id": str(index),
                })
            else:
                entries.append({
                    "file": str(clip),
                    "source": "local_submarine_science_illustration",
                    "source_url": "",
                    "license": "original deterministic vector illustration",
                    "media_type": "local_illustration",
                })
        return entries

    def test_illustration_only_video_fails_even_when_all_scene_files_exist(self):
        report = self.evaluate_manifest(self.make_entries(0))
        self.assertFalse(report["passed"])
        self.assertEqual(report["broll"]["external_media_count"], 0)
        self.assertTrue(any("unique licensed external media assets" in error for error in report["errors"]))
        self.assertTrue(any("scenes use licensed external media" in error for error in report["errors"]))

    def test_unique_licensed_stock_photos_can_satisfy_video_first_fallback_policy(self):
        report = self.evaluate_manifest(self.make_entries(6))
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["broll"]["external_media_count"], 6)
        self.assertEqual(report["broll"]["external_unique_sources"], 6)
        self.assertEqual(report["broll"]["external_scene_share"], 0.75)
        self.assertEqual(report["broll"]["media_type_counts"]["photo"], 6)


if __name__ == "__main__":
    unittest.main()
