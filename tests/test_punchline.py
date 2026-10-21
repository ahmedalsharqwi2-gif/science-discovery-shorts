import unittest
from news.editor import spoken_punchline

class SpokenPunchlineTests(unittest.TestCase):
    def test_observed_spoken_fillers_are_retained(self):
        actual='الجهاز بيكح، وعشان نقدر نعرف إزاي اللي جاي ده هيبوظ.'
        self.assertEqual(spoken_punchline(actual,'عشان نعرف إزاي اللي جاي هيبوظ'),'وعشان نقدر نعرف إزاي اللي جاي ده هيبوظ.')
    def test_changed_meaning_cannot_be_invented(self):
        self.assertIsNone(spoken_punchline('الجهاز مش سريع خالص','الجهاز سريع'))
    def test_missing_word_still_fails(self):
        self.assertIsNone(spoken_punchline('الجهاز سريع','الجهاز قدم استقالته'))
