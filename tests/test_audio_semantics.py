import unittest
from film_factory.sound import speech_cues

class SpokenSoundTests(unittest.TestCase):
 def test_sound_follows_the_actual_word_instead_of_scene_punchline(self):
  words=[{'text':t,'start':i*.5,'end':i*.5+.4} for i,t in enumerate('سمعت خطوات وبعدين لقيت ترباس الباب بيتحرك وبعدها سكت الصوت'.split())]
  cues=speech_cues(words,'horror');self.assertEqual([x['effect'] for x in cues],['footsteps','latch','silence']);self.assertEqual([x['beat'] for x in cues],[.5,2,4])
 def test_firebreak_is_not_triggered_by_a_house_count(self):
  words=[{'text':t,'start':i*.5,'end':i*.5+.4} for i,t in enumerate('تلاتة عشر ألف بيت اتحرقوا'.split())]
  self.assertEqual(speech_cues(words,'history'),[])
if __name__=='__main__':unittest.main()
