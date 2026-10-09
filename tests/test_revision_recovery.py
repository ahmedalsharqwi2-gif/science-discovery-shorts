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

    def test_quality_revisions_restart_from_full_source_and_report_word_count_failure(self):
        generator = ContentGenerator(min_words=6, max_words=8)
        generator.grammar_fixer.fix_text = lambda text: (text, [])
        rejected = SimpleNamespace(overall_score=0.63, issues=['كثافة الأحرف العربية منخفضة: 46%'], warnings=[], is_acceptable=False)
        accepted = SimpleNamespace(overall_score=1.0, issues=[], warnings=[], is_acceptable=True)
        generator.quality_checker.generate_report = unittest.mock.Mock(side_effect=[rejected, rejected, rejected, accepted])
        source = 'هذا نص عربي مليء بالمعلومات المهمة.'
        short_one = 'هذه نسخة مختصرة.'
        short_two = 'هذه نسخة أقصر.'
        with patch('scripts.generate_content.llm_chat', side_effect=[source, short_one, short_two, source]) as llm:
            result = generator.generate_narration('العلم')
        self.assertEqual(result, source)
        self.assertEqual(llm.call_count, 4)
        second_revision_prompt = llm.call_args_list[2].args[0][0]['content']
        self.assertIn(source, second_revision_prompt)
        self.assertNotIn(short_one, second_revision_prompt)
        self.assertIn('3 خارج النطاق الإلزامي 6-8', second_revision_prompt)
        self.assertIn('85%', second_revision_prompt)

    def test_short_quality_rewrites_keep_near_pass_complete_source(self):
        generator = ContentGenerator(min_words=6, max_words=12)
        generator.grammar_fixer.fix_text = lambda text: (text, [])
        rejected = SimpleNamespace(
            overall_score=0.68,
            issues=['كثافة الأحرف العربية منخفضة'],
            warnings=[],
            is_acceptable=False,
        )
        generator.quality_checker.generate_report = unittest.mock.Mock(
            side_effect=[rejected, rejected, rejected, rejected]
        )
        source = 'هذا نص عربي كامل يشرح الفكرة العلمية بوضوح مفيد.'
        with patch(
            'scripts.generate_content.llm_chat',
            side_effect=[source, 'هذه نسخة مختصرة.', 'هذه نسخة أقصر.', 'نص مبتور.'],
        ):
            result = generator.generate_narration('العلم')
        self.assertEqual(result, source)

    def test_shortening_uses_second_attempt_when_first_is_invalid(self):
        generator = ContentGenerator(min_words=20, max_words=40)
        generator.grammar_fixer.fix_text = lambda t: (t, [])
        valid = ' '.join(['كلمة'] * 30) + '.'
        with patch('scripts.generate_content.llm_chat', side_effect=['قصير.', valid]) as llm:
            result = generator.shorten_narration('العلم', 'نص طويل', 30)
        self.assertEqual(result, valid)
        self.assertEqual(llm.call_count, 2)
