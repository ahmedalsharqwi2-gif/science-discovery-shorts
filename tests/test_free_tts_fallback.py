import tempfile
import types
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.free_tts_fallback import google_arabic_voice


class FreeTTSFallbackTests(unittest.TestCase):
    def test_transmits_exact_arabic_text_without_api_key_or_paid_cloud(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "voice.mp3"
            instance = Mock()
            instance.save.side_effect = lambda path: Path(path).write_bytes(b"provider fixture")
            constructor = Mock(return_value=instance)
            with patch.dict(sys.modules, {"gtts": types.SimpleNamespace(gTTS=constructor)}):
                google_arabic_voice("هذا نص عربي مضبوط.", output)
            self.assertTrue(output.exists())
            self.assertEqual(constructor.call_args.kwargs["text"], "هذا نص عربي مضبوط.")
            self.assertEqual(constructor.call_args.kwargs["lang"], "ar")
            self.assertFalse(output.with_suffix(".building.mp3").exists())

    def test_provider_failure_cannot_replace_existing_good_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "voice.mp3"
            output.write_bytes(b"previous good audio")
            constructor = Mock(side_effect=RuntimeError("provider unavailable"))
            with patch.dict(sys.modules, {"gtts": types.SimpleNamespace(gTTS=constructor)}), self.assertRaises(RuntimeError):
                google_arabic_voice("نص.", output)
            self.assertEqual(output.read_bytes(), b"previous good audio")


if __name__ == "__main__":
    unittest.main()
