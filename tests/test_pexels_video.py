import unittest
import types
from unittest.mock import Mock, patch

from scripts.pexels_video import CLIP_SECONDS, MIN_CLIPS, visual_queries, resolve_visual_queries


class PexelsVideoTests(unittest.TestCase):
    def test_botany_topic_has_related_queries_before_general_science(self):
        queries = visual_queries("لماذا تمشي النباتات نحو النور؟ علم النبات وسلوك الخلايا الحساسة للضوء")
        self.assertEqual(len(queries), 3)
        self.assertTrue(all(any(word in q for word in ("plant", "seed", "leaves")) for q in queries))

    def test_space_topic_uses_only_related_queries(self):
        queries = visual_queries("رحلة إلى الفضاء والنجوم")
        self.assertGreaterEqual(len(queries), 3)
        self.assertTrue(all(any(word in query for word in ("space", "astronomy", "nebula", "planet")) for query in queries))

    def test_long_video_requires_more_than_ten_unique_clips(self):
        required = max(MIN_CLIPS, int(90 / CLIP_SECONDS + 0.999))
        self.assertGreater(required, 10)
        self.assertEqual(required, 15)

    def test_short_video_does_not_require_unnecessary_minimum_clips(self):
        required = max(MIN_CLIPS, int(50.4 / CLIP_SECONDS + 0.999))
        self.assertEqual(required, 9)

    def test_clip_reuse_policy_is_documented(self):
        """A search may return fewer unique clips than a full reel needs."""
        self.assertLess(CLIP_SECONDS, 10)

    def test_taste_topic_resolves_with_or_without_diacritics(self):
        for topic in ("لماذا لا تلتصق نكهة الطعام بلسانك طوال اليوم؟",
                      "لِمَاذَا لَا تَلْتَصِقُ نَكْهَةُ الطَّعَامِ بِلِسَانِكَ؟"):
            queries = resolve_visual_queries(topic)
            self.assertEqual(len(queries), 3)
            self.assertIn("tongue", queries[0])

    def test_unfamiliar_topic_uses_bounded_specific_query_plan(self):
        provider = types.ModuleType("llm_gemini")
        provider.pooled_llm_chat = Mock(return_value=
            '["magnet attracting iron", "iron filings magnet", "magnetic field experiment"]')
        with patch.dict("sys.modules", {"llm_gemini": provider}):
            queries = resolve_visual_queries("لماذا يجذب المغناطيس الحديد؟")
        self.assertEqual(len(queries), 3)
        self.assertTrue(all("magnet" in query for query in queries))
        provider.pooled_llm_chat.assert_called_once()

    def test_malformed_query_plan_does_not_select_generic_footage(self):
        provider = types.ModuleType("llm_gemini")
        provider.pooled_llm_chat = Mock(return_value="not JSON")
        with patch.dict("sys.modules", {"llm_gemini": provider}):
            self.assertEqual(resolve_visual_queries("موضوع جديد"), [])

    def test_unknown_topic_has_no_generic_stock_fallback(self):
        self.assertEqual(visual_queries("موضوع غير مصنف بلا كلمات بصرية"), [])


if __name__ == "__main__":
    unittest.main()
