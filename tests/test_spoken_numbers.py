import unittest
from scripts.spoken_numbers import spoken_numbers
class SpokenNumbersTests(unittest.TestCase):
 def test_years_and_thousands_keep_their_numeric_value(self):
  self.assertEqual(spoken_numbers("١٩٤٣"),spoken_numbers("1943"))
  self.assertEqual(spoken_numbers("338,000"),spoken_numbers("338000"))
  self.assertIn("ألف",spoken_numbers("1943"))
 def test_decimal_digits_and_existing_words(self):
  self.assertIn("فاصلة",spoken_numbers("2.05"))
  self.assertNotRegex(spoken_numbers("١٩٤٣ و338,000 و2.05"),r"[0-9٠-٩]")
  self.assertEqual(spoken_numbers("ثلاثة آلاف جندي"),"ثلاثة آلاف جندي")
