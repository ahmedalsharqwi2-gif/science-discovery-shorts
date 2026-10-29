import unittest
from professional_motion.alignment import measured_timing
class MultilingualSpeechTests(unittest.TestCase):
 def test_english_name_and_separate_arabic_clitic_keep_real_anchors(self):
  scenes=[{'narration':'وأني سبوتش ريكوغنايزر الذكاء'} for _ in range(8)]
  actual=[]
  for i in range(8):
   for j,text in enumerate(['و','Any','Speech','Recognizer','الزكاء']):actual.append({'text':text,'start':i*10+j*.4,'end':i*10+j*.4+.3})
  result=measured_timing({'scenes':scenes},90,[('real-ASR-spellings',actual)])
  self.assertEqual(result['coverage'],1);self.assertLess(result['exact_token_coverage'],.85);self.assertTrue(result['known_name_and_egyptian_normalization_applied']);self.assertEqual(result['words'],actual)
 def test_unrelated_speech_is_not_rescued_by_normalization(self):
  story={'scenes':[{'narration':'وأني سبوتش ريكوغنايزر الذكاء'} for _ in range(8)]}
  actual=[{'text':'مختلف','start':i,'end':i+.5} for i in range(32)]
  with self.assertRaises(ValueError):measured_timing(story,90,[('wrong-speech',actual)])

 def test_different_unknown_english_names_cannot_match_as_empty_tokens(self):
  story={'scenes':[{'narration':'Alpha Beta Gamma Delta'} for _ in range(8)]}
  actual=[{'text':'WrongBrand','start':i,'end':i+.5} for i in range(32)]
  with self.assertRaises(ValueError):measured_timing(story,90,[('different-names',actual)])
