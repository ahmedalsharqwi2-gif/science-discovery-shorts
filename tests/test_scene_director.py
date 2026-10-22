import unittest
from film_factory.scene_director import shots
class CinematicDirectorTest(unittest.TestCase):
 def test_artillery_has_real_motion_requirement(self):
  d=shots({"scenes":[{"start":0,"end":6,"title":"معركة"}],"words":[{"start":1.4,"text":"المدافع"},{"start":2,"text":"بتضرب"}]},"history")
  self.assertEqual(d[0]["subject"],"artillery")
  self.assertEqual(d[0]["cue_at"],1.4)
  self.assertIn("muzzle_flash",d[0]["assets_required"])
  self.assertTrue(d[0]["no_static_photo_as_action"])
 def test_neural_signal(self):
  d=shots({"scenes":[{"start":0,"end":4,"title":"x"}],"words":[{"start":.6,"text":"الأعصاب"}]},"science")
  self.assertEqual(d[0]["subject"],"neuron")
  self.assertEqual(d[0]["sound"],"electric_pulse")
 def test_shots_derive_from_correct_scene(self):
  d=shots({"scenes":[{"start":0,"end":3,"title":"x"},{"start":3,"end":7,"title":"x"}],"words":[{"start":1,"text":"خريطة"},{"start":4,"text":"مدفع"}]},"history")
  self.assertEqual([x["subject"] for x in d],["map","artillery"])
if __name__=="__main__":unittest.main()
