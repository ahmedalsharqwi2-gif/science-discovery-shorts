import unittest
from scripts.narration_recovery import fit_complete_sentences


class RecoveryTests(unittest.TestCase):
    def test_keeps_opening_and_conclusion_without_new_words(self):
        text = "كيف يعمل هذا الجهاز؟ يعمل بقوة ضغط الماء. وتوجد تفاصيل إضافية كثيرة هنا. وهذه هي النتيجة النهائية."
        result = fit_complete_sentences(text, 12, 16)
        self.assertTrue(result.startswith("كيف يعمل هذا الجهاز؟"))
        self.assertTrue(result.endswith("وهذه هي النتيجة النهائية."))
        self.assertNotIn("تفاصيل", result)

    def test_never_cuts_an_overlong_sentence(self):
        self.assertIsNone(fit_complete_sentences("هذه جملة واحدة طويلة لا يجوز قطعها هنا.", 2, 3))

    def test_rejects_incomplete_tail(self):
        self.assertIsNone(fit_complete_sentences("افتتاحية صحيحة. ثم نص مبتور", 2, 8))

    def test_rejects_too_short_result(self):
        self.assertIsNone(fit_complete_sentences("نص قصير.", 4, 10))


if __name__ == "__main__":
    unittest.main()
