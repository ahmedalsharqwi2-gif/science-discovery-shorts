"""The approved narration must stay complete and must never switch voices."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import generate_voice as voice

class ApprovedNarrationTests(unittest.TestCase):
    def test_one_complete_request_and_provider_failure_propagates(self):
        with tempfile.TemporaryDirectory() as folder:
            engine=voice.VoiceGenerator(Path(folder))
            with patch('voice_provider.client.generate') as generate:
                path,ok=engine.generate("أول جملة. آخر جملة.")
                self.assertTrue(ok)
                self.assertEqual(generate.call_args.args[0],"أول جملة. آخر جملة.")
                self.assertEqual(generate.call_count,1)
            with patch('voice_provider.client.generate',side_effect=RuntimeError('quota')):
                with self.assertRaisesRegex(RuntimeError,'quota'):
                    engine.generate("النص كامل")
