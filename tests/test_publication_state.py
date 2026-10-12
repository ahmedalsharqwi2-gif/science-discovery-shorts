import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import publication_state as state


class PublicationReceiptsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(patch.stopall)
        self.root = Path(self.temp.name)
        patch.object(state, "ROOT", self.root).start()
        patch.dict(os.environ, {"PUBLISH_DUE_AT": "2026-10-13T09:00:00Z", "PUBLISH_IMMEDIATE": "false", "BUFFER_OUTCOME": "success", "YOUTUBE_OUTCOME": "success"}).start()

    def test_generated_media_alone_does_not_confirm_reserve(self):
        with self.assertRaises(FileNotFoundError):
            state.confirm_stock()

    def test_real_receipts_and_successful_steps_confirm_exact_slot(self):
        state.record_receipt("facebook", "post-1", "2026-10-13T09:00:00Z")
        state.record_receipt("youtube", "video-2", "2026-10-13T09:00:00Z")
        state.confirm_stock()
        data = json.loads((self.root / "state/publication_stock.json").read_text())
        self.assertTrue(data["slots"]["stock 2026-10-13 12 Cairo"]["confirmed"])

    def test_partial_failure_is_not_counted_as_stock(self):
        state.record_receipt("facebook", "post-1")
        with patch.dict(os.environ, {"YOUTUBE_OUTCOME": "failure"}), self.assertRaises(RuntimeError):
            state.confirm_stock()
        data = json.loads((self.root / "state/publication_stock.json").read_text())
        self.assertFalse(data["slots"][state.stock_key()]["confirmed"])

    def test_missing_provider_identifier_cannot_look_successful(self):
        with self.assertRaises(ValueError):
            state.record_receipt("facebook", "")


if __name__ == "__main__":
    unittest.main()
