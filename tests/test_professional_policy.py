import json,os,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch
from professional_motion.policy import require_duration
from professional_motion.news_policy import require_fresh,choose,validate_memes
from professional_motion.metadata import make
from professional_motion.merge_chunks import check_intervals
from professional_motion.alignment import measured_timing
from professional_motion.fiction import validate_scares

class LengthAndMetadataTests(unittest.TestCase):
 def test_exact_boundary_durations_are_rejected(self):
  for n in (0,89.9,90,180,181,float('nan')):
   with self.assertRaises(ValueError):require_duration(n)
  for n in (90.01,120,179.99):self.assertEqual(require_duration(n),n)
 def test_title_and_hashtags_describe_the_actual_subject(self):
  s={'title':'جسر الرومان فوق النهر','canonical_subject':'roman-bridge','scenes':[{'narration':'الجسر ده بناه الرومان فوق النهر'}],'hashtags':['الرومان','النهر','تاريخ'],'source':{'publisher':'UNESCO','url':'https://whc.unesco.org/en/list/344/'}}
  m=make(s,'history');self.assertIn('جسر الرومان',m['title']);self.assertIn('#الرومان',m['caption']);self.assertLessEqual(len(m['title']),100)
 def test_original_horror_has_no_invented_documentary_source_or_intrusive_genre_notice(self):
  s={'title':'الإنتركم ورا باب الممر','scenes':[{'narration':'الإنتركم ده بيرد من باب الممر'}],'hashtags':['الإنتركم','باب_الممر','رعب'],'fiction':True,'source':{'kind':'original_fiction','publisher':'ملفات غامضة'}}
  m=make(s,'horror');self.assertEqual(m['source_url'],'');self.assertNotIn('خيالية',m['caption']);self.assertNotIn('المصدر:',m['caption'])
 def test_irrelevant_reach_bait_tags_are_rejected(self):
  s={'title':'خبر جديد','scenes':[{'narration':'خبر جديد'}],'hashtags':['viral','fyp','ترند'],'source':{}}
  with self.assertRaises(ValueError):make(s,'news')

class NewsRelevanceTests(unittest.TestCase):
 def setUp(self):self.now=datetime(2026,10,29,8,tzinfo=timezone.utc)
 def test_old_undated_and_future_news_cannot_pass_as_current(self):
  for row in ({},{'published':(self.now-timedelta(hours=49)).isoformat()},{'published':(self.now+timedelta(hours=1)).isoformat()},{'published':'2026-10-29'}):
   with self.assertRaises(ValueError):require_fresh(row,self.now)
  require_fresh({'published':(self.now-timedelta(hours=24)).isoformat()},self.now)
 def test_ranking_cannot_invent_a_story_url_or_pick_minor_promotional_news(self):
  row={'title':'Major model release','publisher':'OpenAI','url':'https://openai.com/index/release/','published':self.now.isoformat(),'summary':'New public model release'}
  def rank(prompt,schema):return {'selected':[{'index':0,'importance':4,'reason':'Capability release'},{'index':99,'importance':5,'reason':'invented'},{'index':0,'importance':3,'reason':'minor'}]}
  selected=choose([row],rank,self.now);self.assertEqual(len(selected),1);self.assertEqual(selected[0]['url'],row['url'])
 def test_no_fresh_important_news_does_not_trigger_an_invented_fallback(self):
  self.assertEqual(choose([],lambda *a:(_ for _ in ()).throw(AssertionError('must not call')),self.now),[])
 def test_a_plain_bulletin_does_not_pass_the_meme_requirement(self):
  with self.assertRaises(ValueError):validate_memes({'scenes':[{'narration':'خبر حقيقي بدون قفشة'}]*8})
 def test_visual_jokes_must_be_spoken_and_distinct(self):
  jokes=['المحفظة حضرت الاجتماع','الكود طالب أجازة','البنشمارك محتاج حكم','السيرفر بيشرب قهوة']
  s={'scenes':[{'narration':'ده التعليق '+j,'punchline':j,'reaction':'shock'} for j in jokes]};validate_memes(s)
  s['scenes'][0]['punchline']='كلام لم يقله الراوي'
  with self.assertRaises(ValueError):validate_memes(s)

class ExactFramesAndRevealsTests(unittest.TestCase):
 def test_partitions_reject_gaps_and_duplicated_frames(self):
  check_intervals([{'start_frame':0,'end_frame':4},{'start_frame':4,'end_frame':9}],9)
  for rows in ([{'start_frame':0,'end_frame':4},{'start_frame':5,'end_frame':9}],[{'start_frame':0,'end_frame':5},{'start_frame':4,'end_frame':9}],[{'start_frame':0,'end_frame':8}]):
   with self.assertRaises(ValueError):check_intervals(rows,9)
 def test_horror_and_meme_beats_follow_actual_recognized_words(self):
  words='ده باب الممر اللي اتفتح لوحده وأنا واقف قدامه ساكت'.split();s={'scenes':[{'narration':' '.join(words),'scare_phrase':'اتفتح لوحده','punchline':'قدامه ساكت'}]}
  actual=[{'text':w,'start':float(i),'end':i+.5} for i,w in enumerate(words)]
  t=measured_timing(s,15,[('measured',actual)]);self.assertEqual(t['scenes'][0]['scare_beat'],4);self.assertEqual(t['scenes'][0]['meme_beat'],8)
 def test_horror_requires_multiple_different_spoken_reveals(self):
  s={'title':'الممر','plot_signature':'a new original story about a corridor whose hidden door changes each attempt to leave','scenes':[{'narration':'سمعت الباب بيتفتح لوحده','scare_phrase':'بيتفتح لوحده'}]*3}
  with self.assertRaises(ValueError):validate_scares(s)

if __name__=='__main__':unittest.main()
