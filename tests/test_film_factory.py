import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from film_factory.editor import validate,BRIEFS
from film_factory.produce import performance
from film_factory.sound import build

def fixture(profile='horror'):
 words='أنا واقف جنب الباب ومش قادر أتنفس بصيت للموبايل لقيت الشاشة سودة سمعت خطوات جاية من الناحية التانية قفلت النور عشان محدش يسمعني بس الصوت قرب أكتر وأنا مكنتش فاهم إزاي ده بيحصل دلوقتي'.split()
 words+=['لسه','واقف','مكاني','ومش','عارف','أتحرك','ولا','أعمل','أي','حاجة']
 return {'title':'الصوت ورا الباب','scenes':[{'title':'الباب المقفول','narration':' '.join(words),'labels':['الباب'],'cue':'سمعت خطوات','delivery':'panic_whisper','effect':'footsteps','image_prompt':'A live action photographic first person view of a navy sleeved hand next to an old walnut apartment door in a narrow beige Egyptian corridor at night, weak warm bulb, quiet practical lighting, no writing.'} for _ in range(6)]}

class FilmTests(unittest.TestCase):
 def test_cue_is_always_real_speech_even_if_model_misquotes_it(self):
  p=fixture();p['scenes'][0]['cue']='كلام لم يتم نطقه';p=validate(p,'horror',BRIEFS['horror'])
  self.assertIn(p['scenes'][0]['cue'],p['scenes'][0]['narration']);self.assertTrue(p['fiction'])
 def test_whisper_direction_uses_exact_spoken_anchors_without_changing_script(self):
  p=validate(fixture(),'horror',BRIEFS['horror']);before=p['narration'];style=performance(p)
  self.assertIn('terrified',style);self.assertIn(' '.join(p['scenes'][0]['narration'].split()[:7]),style);self.assertEqual(before,p['narration'])
 def test_perfect_accuracy_claim_is_rejected(self):
  p=fixture('science');p['scenes'][0]['narration']+=' من غير أي غلطة'
  with self.assertRaisesRegex(ValueError,'Unsupported'):validate(p,'science',BRIEFS['science'])
 def test_effects_follow_actual_audio_beats(self):
  with tempfile.TemporaryDirectory() as td:
   import os,wave
   before=os.getcwd();os.chdir(td);Path('output').mkdir()
   try:
    r=build(6,[{'effect':'knock','beat':2.25,'cue':'خبط الباب'}],'horror');self.assertEqual([e['at'] for e in r['events']],[2.25,2.67])
    with wave.open('output/effects.wav') as w:self.assertEqual(w.getnchannels(),2);self.assertEqual(w.getnframes(),144000)
   finally:os.chdir(before)

if __name__=='__main__':unittest.main()
