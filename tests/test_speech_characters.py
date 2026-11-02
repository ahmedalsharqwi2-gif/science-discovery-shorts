import unittest
from professional_motion.speech_characters import character_timing
class SpeechCharacterTests(unittest.TestCase):
 def fixture(self):
  tokens=['الكلمة'+chr(0x0627+i%25)+chr(0x0627+i//25) for i in range(96)]
  story={'scenes':[{'id':str(i),'narration':' '.join(tokens[i*12:(i+1)*12])} for i in range(8)]}
  return tokens,story
 def test_split_recognized_words_retain_measured_time_and_full_evidence(self):
  words,story=self.fixture();raw=[]
  for i,word in enumerate(words):raw.extend([{'text':word[:3],'start':i,'end':i+.35},{'text':word[3:],'start':i+.35,'end':i+.8}])
  result=character_timing(story,96,[('real-ASR',raw)],lambda x:x)
  self.assertEqual(result['coverage'],1);self.assertEqual(result['normalized_character_coverage'],1)
  self.assertEqual(result['words'],raw);self.assertEqual(result['caption_groups'][0]['end'],5.8)
 def test_unrelated_recognition_is_rejected(self):
  words,story=self.fixture();raw=[{'text':'unrelated','start':i,'end':i+.8} for i in range(96)]
  with self.assertRaises(ValueError):character_timing(story,96,[('ASR',raw)],lambda x:x)
 def test_missing_half_the_script_is_not_filled_from_supplied_text(self):
  words,story=self.fixture();raw=[{'text':w,'start':i,'end':i+.8} for i,w in enumerate(words) if i%2==0]
  with self.assertRaises(ValueError):character_timing(story,96,[('ASR',raw)],lambda x:x)
 def test_corrupt_raw_timeline_is_rejected(self):
  words,story=self.fixture();raw=[{'text':w,'start':95-i,'end':96-i} for i,w in enumerate(words)]
  with self.assertRaises(ValueError):character_timing(story,96,[('ASR',raw)],lambda x:x)
 def test_overlapping_measured_phrase_boundaries_stay_readable(self):
  words,story=self.fixture();raw=[{'text':w,'start':i*.3,'end':i*.3+.4} for i,w in enumerate(words)]
  result=character_timing(story,29,[('ASR',raw)],lambda x:x)
  captions=result['caption_groups']
  self.assertEqual(' '.join(c['text'] for c in captions),' '.join(words))
  self.assertTrue(all(a['end']<=b['start'] for a,b in zip(captions,captions[1:])))
  self.assertTrue(all(0<c['end']-c['start'] and len(c['text'].split())<=18 for c in captions))
if __name__=='__main__':unittest.main()

