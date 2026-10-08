import unittest
from types import SimpleNamespace
from unittest.mock import patch
from arabic_tts_quality_checker import ArabicTTSQualityChecker
from scripts.generate_content import ContentGenerator


class RevisionRecoveryTests(unittest.TestCase):
    def test_alef_wasla_and_tashkeel_are_arabic(self):
        text = 'ٱلْعِلْمُ ٱلْفَضَاءُ ٱلْبَحْرُ ٱلْأَرْضُ'
        score, issues, _ = ArabicTTSQualityChecker().check_text_quality(text)
        self.assertEqual(issues, [])
        self.assertEqual(score, 1.0)

    def test_foreign_text_is_still_detected(self):
        _, issues, _ = ArabicTTSQualityChecker().check_text_quality('science space engineering العربية')
        self.assertTrue(issues)

    def test_oversized_revision_recovers_without_cutting_words(self):
        generator = ContentGenerator(min_words=4, max_words=6)
        generator.grammar_fixer.fix_text = lambda t: (t, [])
        bad = SimpleNamespace(overall_score=0.7, issues=['quality issue'], is_acceptable=False)
        good = SimpleNamespace(overall_score=1.0, issues=[], is_acceptable=True)
        generator.quality_checker.generate_report = unittest.mock.Mock(side_effect=[bad, good])
        with patch('scripts.generate_content.llm_chat', side_effect=['هذه جملة عربية كاملة مفيدة.', 'هذه جملة عربية كاملة مفيدة. وهذه زيادة لا نحتاج إليها.']):
            result = generator.generate_narration('العلم')
        self.assertEqual(result, 'هذه جملة عربية كاملة مفيدة.')

    def test_revision_without_boundary_retries_and_rechecks_quality(self):
        generator = ContentGenerator(min_words=4, max_words=6)
        generator.grammar_fixer.fix_text = lambda t: (t, [])
        bad = SimpleNamespace(overall_score=0.7, issues=['quality issue'], is_acceptable=False)
        good = SimpleNamespace(overall_score=1.0, issues=[], is_acceptable=True)
        generator.quality_checker.generate_report = unittest.mock.Mock(side_effect=[bad, good, good])
        with patch('scripts.generate_content.llm_chat', side_effect=['هذه جملة عربية كاملة مفيدة.', 'هذه جملة عربية طويلة جدا ليس فيها أي نهاية آمنة', 'هذه جملة عربية كاملة مفيدة.']) as llm:
            result = generator.generate_narration('العلم')
        self.assertEqual(result, 'هذه جملة عربية كاملة مفيدة.')
        self.assertEqual(llm.call_count, 3)

    def test_shortening_uses_second_attempt_when_first_is_invalid(self):
        generator = ContentGenerator(min_words=20, max_words=40)
        generator.grammar_fixer.fix_text = lambda t: (t, [])
        valid = ' '.join(['كلمة'] * 30) + '.'
        with patch('scripts.generate_content.llm_chat', side_effect=['قصير.', valid]) as llm:
            result = generator.shorten_narration('العلم', 'نص طويل', 30)
        self.assertEqual(result, valid)
        self.assertEqual(llm.call_count, 2)
