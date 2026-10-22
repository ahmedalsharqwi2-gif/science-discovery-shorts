import tempfile
import unittest
from pathlib import Path
from film_factory.motion_kit_timeline import timeline, save

class MotionKitTimelineTests(unittest.TestCase):
    def test_profiles_emit_vertical_timeline(self):
        timing={"duration":10.0,"words":[{"text":"مرحبا","start":0.1,"end":0.5}],
                "scenes":[{"start":0,"end":5,"beat":3},{"start":5,"end":10}]}
        for profile in ("science","history","horror","news"):
            with self.subTest(profile=profile):
                item=timeline(timing,profile)
                self.assertEqual(item["format"]["width"],1080)
                self.assertEqual(item["format"]["height"],1920)
                self.assertEqual(item["format"]["fps"],30)
                self.assertEqual(len(item["events"]),3)
                with tempfile.TemporaryDirectory() as d:
                    self.assertEqual(save(timing,profile,Path(d)/"timeline.json")["profile"],profile)
    def test_bad_time_rejected(self):
        with self.assertRaises(ValueError):
            timeline({"duration":4,"words":[{"text":"x","start":3,"end":9}]},"news")
if __name__=="__main__":unittest.main()
