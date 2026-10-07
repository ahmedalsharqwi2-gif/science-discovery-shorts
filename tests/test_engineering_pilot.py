import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.generate_content import ENGINEERING_PILOT_TOPICS, ContentGenerator, select_engineering_pilot

class EngineeringPilotTests(unittest.TestCase):
    def test_six_engineering_topics_alternate_with_nature_and_then_finish(self):
        history = []
        self.assertEqual(len(ENGINEERING_PILOT_TOPICS), 12)
        for expected in ENGINEERING_PILOT_TOPICS:
            self.assertEqual(select_engineering_pilot(history), expected)
            history.append({"title": expected})
        self.assertIsNone(select_engineering_pilot(history))

    def test_workflow_switch_selects_pilot_without_llm_call(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ENGINEERING_PILOT_ENABLED": "true"}), patch("scripts.generate_content.llm_chat") as llm:
            generator = ContentGenerator(topic_history_path=Path(directory) / "history.json")
            self.assertEqual(generator.generate_topic(), ENGINEERING_PILOT_TOPICS[0])
            llm.assert_not_called()

    def test_explicit_category_keeps_dynamic_selection(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {"ENGINEERING_PILOT_ENABLED": "true", "TOPIC_BANK_REQUIRED": "false"}), patch("scripts.generate_content.llm_chat", return_value="كيف تتكون النجوم؟") as llm:
            generator = ContentGenerator(topic_history_path=Path(directory) / "history.json")
            self.assertEqual(generator.generate_topic("الفضاء"), "كيف تتكون النجوم؟")
            llm.assert_called_once()
