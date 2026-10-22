import unittest
from PIL import Image
from film_factory.cinematic_overlay import over
class CinematicOverlayTests(unittest.TestCase):
    def test_all_profiles_render_rgba_frame(self):
        for name in ("science","history","horror","news"):
            with self.subTest(name=name):
                frame=Image.new("RGBA",(360,640),(10,12,20,255))
                old=frame.tobytes()
                result=over(frame,1.5,{"start":0,"end":6},name)
                self.assertEqual(result.size,(360,640))
                self.assertNotEqual(result.tobytes(),old)
    def test_ended_scene_has_no_overlay(self):
        frame=Image.new("RGBA",(360,640),(0,0,0,255))
        old=frame.tobytes()
        over(frame,7,{"start":0,"end":6},"news")
        self.assertEqual(frame.tobytes(),old)
if __name__ == "__main__": unittest.main()
