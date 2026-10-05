import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.clip_review import clip_digest, review_clip
from scripts.media_audio import ducking_filters, normalized_audio_args


class ClipReviewTests(unittest.TestCase):
    def test_missing_review_does_not_approve_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "clip.mp4"
            clip.write_bytes(b"candidate")
            with patch("scripts.clip_review.analyze_clip", return_value=None), patch("scripts.clip_review.ROOT", root), patch.dict("os.environ", {"CLIP_REVIEW_MANIFEST": str(root / "reviews.json")}):
                with self.assertRaisesRegex(ValueError, "REQUIRED"):
                    review_clip(clip, "castle", "story")
                self.assertTrue((root / "state/clip_review_requests.json").exists())

    def test_approval_cannot_be_reused_for_changed_bytes_or_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            clip = root / "clip.mp4"
            clip.write_bytes(b"reviewed")
            manifest = root / "reviews.json"
            record = {"status": "PASS", "keyword": "castle", "topic": "story", "reviewer": "editor",
                      "reason": "actual scene inspected", "audio_decision": "VOICE ONLY", "checks": dict.fromkeys(("subject", "location", "activity", "symbols"), True)}
            manifest.write_text(json.dumps({clip_digest(clip): record}))
            with patch("scripts.clip_review.analyze_clip", return_value=None), patch("scripts.clip_review.ROOT", root), patch.dict("os.environ", {"CLIP_REVIEW_MANIFEST": str(manifest)}):
                self.assertEqual(review_clip(clip, "castle", "story")["audio_decision"], "VOICE ONLY")
                with self.assertRaises(ValueError):
                    review_clip(clip, "castle", "another story")
                clip.write_bytes(b"replaced")
                with self.assertRaises(ValueError):
                    review_clip(clip, "castle", "story")

    def test_ducking_compresses_scene_audio_and_splits_narration(self):
        graph = ";".join(ducking_filters("[0:a]", "[1:a]"))
        self.assertIn("asplit=2[voice][sidechain]", graph)
        self.assertIn("[original][sidechain]sidechaincompress", graph)

    def test_muted_clip_has_silent_stereo_stream_for_concatenation(self):
        extra, mapping = normalized_audio_args(Path("muted.mp4"), False)
        self.assertIn("anullsrc=r=48000:cl=stereo", extra)
        self.assertEqual(mapping[mapping.index("-map") + 1], "1:a:0")


class ExplicitAudioDecisionTests(unittest.TestCase):
    def test_missing_audio_decision_is_rejected(self):
        from scripts.clip_review import _validate_audio
        with self.assertRaises(ValueError):
            _validate_audio({"status": "PASS"})
