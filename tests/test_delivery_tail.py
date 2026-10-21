import unittest
import numpy as np
from scripts.verify_delivery import tail_score,RATE
class DeliveryTailTests(unittest.TestCase):
 def voice(self):
  t=np.arange(8*RATE)/RATE
  return .3*np.sin(2*np.pi*(110*t+23*t*t))*(.7+.3*np.sin(t*4))
 def test_music_and_encoding_scale_preserve_the_spoken_tail(self):
  a=self.voice();t=np.arange(len(a))/RATE
  self.assertGreater(tail_score(a,.8*a+.015*np.sin(2*np.pi*55*t)),.85)
 def test_silence_padding_cannot_hide_missing_final_words(self):
  a=self.voice();b=a.copy();b[-3*RATE:]=0
  with self.assertRaises(ValueError):tail_score(a,b)
