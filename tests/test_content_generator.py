import unittest
from unittest.mock import patch

from scripts.generate_content import (
    CHANNEL_BRIEF,
    EDITORIAL_SAFETY_BOUNDARY,
    TOPIC_CATEGORIES,
    ContentGenerator,
    normalize_narration_response,
    normalize_topic_response,
)


class ContentGeneratorTopicPolicyTests(unittest.TestCase):
    def test_normalize_topic_response_removes_model_wrappers(self):
        self.assertEqual(
            normalize_topic_response('**العنوان:** "أسرار المحيط"'),
            "أسرار المحيط",
        )
        self.assertEqual(
            normalize_topic_response('{"title": "الثقوب السوداء"}'),
            "الثقوب السوداء",
        )

    def test_normalize_narration_response_unwraps_escaped_json(self):
        raw = r'{"narration":"نص عربي.\\nجملة ثانية."}'
        self.assertEqual(normalize_narration_response(raw), "نص عربي.\nجملة ثانية.")

    def test_normalize_narration_response_extracts_malformed_json_like_wrapper(self):
        raw = '{"narration": "نص عربي عن النوم", "extra": {"x": 1}} trailing'
        self.assertEqual(normalize_narration_response(raw), "نص عربي عن النوم")

    def test_channel_brief_and_topic_bank_are_used(self):
        with patch(
            "scripts.generate_content.llm_chat",
            return_value="عنوان جذاب\nشرح علمي موجز",
        ) as llm:
            ContentGenerator().generate_topic()

        prompt = llm.call_args.args[0][0]["content"]
        self.assertIn("أسرار الفضاء", CHANNEL_BRIEF)
        self.assertIn(CHANNEL_BRIEF, prompt)
        self.assertGreaterEqual(len(TOPIC_CATEGORIES), 10)
        self.assertIn("أعماق المحيطات", prompt)
        self.assertIn("الذكاء الاصطناعي", prompt)
        self.assertIn("قابلة للتحقق", prompt)

    def test_aerospace_and_naval_tracks_are_safe_and_prompted(self):
        with patch(
            "scripts.generate_content.llm_chat",
            return_value="كيف تتحمل الغواصة ضغط الأعماق؟",
        ) as llm:
            ContentGenerator().generate_topic("الهندسة البحرية")

        prompt = llm.call_args.args[0][0]["content"]
        self.assertIn("الطائرات الحربية", prompt)
        self.assertIn("السفن", prompt)
        self.assertIn("الغواصات", prompt)
        self.assertIn(EDITORIAL_SAFETY_BOUNDARY, prompt)
        self.assertIn("لا تمجّد العنف", prompt)

    def test_narration_removes_production_labels_and_normalizes_ant_collective(self):
        from scripts.generate_content import normalize_narration_response
        result = normalize_narration_response("STORY: كيف تتواصل النملات؟ Voiceover: النملات تستخدم إشارات.")
        self.assertNotIn("STORY", result.upper())
        self.assertNotIn("VOICEOVER", result.upper())
        self.assertIn("النمل", result)
        self.assertNotIn("النملات", result)


if __name__ == "__main__":
    unittest.main()
