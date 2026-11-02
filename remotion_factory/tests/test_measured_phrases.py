import unittest
from remotion_factory.speech_characters import character_timing
class MeasuredPhraseTests(unittest.TestCase):
 def test_unmatched_terminal_word_does_not_create_an_unanchored_singleton_caption(self):
  words=['word'+chr(0x0627+i%25)+chr(0x0627+i//25) for i in range(97)]
  story={'scenes':[{'id':str(i),'narration':' '.join(words[i*12:(i+1)*12])} for i in range(7)]+[{'id':'7','narration':' '.join(words[84:])}]}
  actual=[{'text':w if i<96 else 'unrecognized-final-word','start':i,'end':i+.7} for i,w in enumerate(words)]
  result=character_timing(story,97, [('independent-asr',actual)],lambda v:v)
  self.assertGreaterEqual(result['coverage'],.9)
  self.assertEqual(' '.join(x['text'] for x in result['caption_groups']),' '.join(words))
  self.assertIn(words[-1],result['unmatched_script_words'])
  self.assertEqual(result['caption_groups'][-1]['end'],97)
  self.assertEqual(result['words'],actual)
 def test_unrelated_speech_stays_rejected(self):
  story={'scenes':[{'id':'a','narration':' '.join('expected'+str(i) for i in range(60))}]}
  raw=[{'text':'unrelated','start':i,'end':i+.5} for i in range(60)]
  with self.assertRaises(ValueError):character_timing(story,61,[('real-asr',raw)],lambda v:v)
if __name__=='__main__':unittest.main()
