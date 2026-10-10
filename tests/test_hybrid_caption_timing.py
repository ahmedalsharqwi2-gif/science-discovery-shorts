import importlib.util
import sys
import tempfile
import types
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
_edge_tts = types.ModuleType("edge_tts")
_edge_tts.Communicate = lambda *args, **kwargs: None
sys.modules.setdefault("edge_tts", _edge_tts)

spec = importlib.util.spec_from_file_location(
    "hybrid_vertical_pipeline_test", ROOT / "scripts" / "hybrid_vertical_pipeline.py"
)
pipeline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pipeline
spec.loader.exec_module(pipeline)


class HybridCaptionTimingTests(unittest.TestCase):
    def test_internal_normalization_does_not_change_display_tokens(self):
        original = "إِكْتُشافـٌ،"
        self.assertEqual(pipeline.normalize_match_word(original), "اكتشاف")
        self.assertEqual(original, "إِكْتُشافـٌ،")

    def test_caption_groups_keep_original_words_and_respect_limits(self):
        words = "حضارة عظيمة... لكن أين اختفت؟".split()
        spans = [
            {"text": word, "start": index * 0.3, "end": (index + 1) * 0.3}
            for index, word in enumerate(words)
        ]
        chunks = pipeline._caption_chunks(spans, max_words=4, max_chars=38)
        self.assertEqual(" ".join(chunk["text"] for chunk in chunks), " ".join(words))
        self.assertTrue(all(len(chunk["text"].split()) <= 4 for chunk in chunks))
        self.assertTrue(all(len(chunk["text"]) <= 38 for chunk in chunks))

    def test_missing_whisper_uses_character_weighted_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            audio = Path(folder) / "voice.mp3"
            audio.touch()
            with mock.patch.dict(sys.modules, {"faster_whisper": None}):
                spans, method = pipeline._whisper_word_spans(audio, "نور وظلام", 2.0)
        self.assertEqual(method, "estimated_fallback")
        self.assertEqual([span["text"] for span in spans], ["نور", "وظلام"])
        self.assertAlmostEqual(spans[0]["start"], 0.0)
        self.assertAlmostEqual(spans[-1]["end"], 2.0)

    def test_event_validation_rejects_empty_and_invalid_events(self):
        with self.assertRaises(ValueError):
            pipeline.validate_caption_events([{"text": " ", "start": 0, "end": 1}], 2)
        with self.assertRaises(ValueError):
            pipeline.validate_caption_events([{"text": "نص", "start": 1, "end": 0.5}], 2)
        with self.assertRaisesRegex(ValueError, "four-word"):
            pipeline.validate_caption_events([{"text": "واحد اثنان ثلاثة أربعة خمسة", "start": 0, "end": 1}], 2)

    def test_ass_output_keeps_arabic_and_adds_short_fade(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "captions.ass"
            pipeline.write_ass([{"text": "أين اختفت؟", "start": 0, "end": 1.0, "highlight_words": ["اختفت"]}], target)
            content = target.read_text(encoding="utf-8")
        self.assertIn("أين", content)
        self.assertIn(r"\fad(120,150)", content)
        self.assertIn(r"{\c&H000000FF&}اختفت{\c}", content)
        self.assertIn("Noto Naskh Arabic", content)


if __name__ == "__main__":
    unittest.main()
