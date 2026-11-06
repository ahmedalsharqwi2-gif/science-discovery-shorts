import unittest
from caption_policy import CaptionEvent, validate_event, assert_bbox_in_safe_zone

class CaptionPolicyTests(unittest.TestCase):
    def test_four_words_and_minimum_duration_pass(self):
        self.assertEqual(validate_event(CaptionEvent(0.0, 1.0, "هذه أربع كلمات فقط")).end, 1.0)

    def test_too_many_words_raise(self):
        with self.assertRaises(ValueError): validate_event(CaptionEvent(0.0, 1.0, "واحدة اثنتان ثلاث أربع خمس"))

    def test_short_event_is_reported(self):
        with self.assertRaises(ValueError): validate_event(CaptionEvent(0.0, 0.5, "كلمتان فقط"))

    def test_shared_safe_zone_and_lower_band(self):
        assert_bbox_in_safe_zone("caption", (190, 1073, 780, 1248))
        with self.assertRaises(ValueError): assert_bbox_in_safe_zone("caption", (190, 1073, 850, 1248))
        with self.assertRaises(ValueError): assert_bbox_in_safe_zone("caption", (190, 900, 780, 1560))
        assert_bbox_in_safe_zone("chrome", (190, 140, 300, 180), kind="chrome")

if __name__ == "__main__": unittest.main()
