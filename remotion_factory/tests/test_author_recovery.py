import unittest
from unittest.mock import patch
from remotion_factory.author import validate,author
class RetainedDraft(unittest.TestCase):
 def test_natural_length_preflight_does_not_require_old270_word_target(self):
  story={'canonical_subject':'stickman-whatif-phone-consequences','scenes':[{'label':'فرضية جديدة','narration':' '.join(['كلمة']*33),'labels':['شاشة','بطارية'],'diagram':'flow'} for _ in range(8)]}
  validate(story,'stickman','خيال معلن')
 def test_unacknowledged_writing_call_is_not_repeated(self):
  with patch('remotion_factory.author.local',return_value={'episodes':{'slot':{'status':'author_requested'}}}),patch('remotion_factory.author.ask_once') as ask:
   with self.assertRaisesRegex(ValueError,'unacknowledged'):author({'slot':'slot','profile':'stickman'},{})
   ask.assert_not_called()
if __name__=='__main__':unittest.main()
