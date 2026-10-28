import json,os,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from professional_motion.cli import decision
from professional_motion import editorial as e
from professional_motion.publisher import approved

class DailyProfessionalTests(unittest.TestCase):
 def test_review_never_publishes_even_when_release_is_approved(self):
  with patch('professional_motion.cli.approved',return_value=True):
   d=decision('history','review','workflow_dispatch');self.assertTrue(d['run']);self.assertFalse(d['publish'])
 def test_no_input_bypasses_pending_human_review(self):
  with patch('professional_motion.cli.approved',return_value=False):
   for event in ('schedule','workflow_dispatch'):
    d=decision('horror','daily',event);self.assertFalse(d['run']);self.assertFalse(d['publish'])
 def test_cairo_noon_guard_selects_one_utc_cron_in_each_season(self):
  with patch('professional_motion.cli.approved',return_value=True):
   for month,hour in ((7,9),(12,10)):
    d=decision('science','daily','schedule',datetime(2026,month,1,hour,tzinfo=timezone.utc));self.assertTrue(d['run'])
    wrong=decision('science','daily','schedule',datetime(2026,month,1,hour+1,tzinfo=timezone.utc));self.assertFalse(wrong['run'])
 def test_scheduled_due_is_exactly_five_cairo_including_dst_transition(self):
  from zoneinfo import ZoneInfo
  with patch('professional_motion.cli.approved',return_value=True):
   for day in (28,29,30,31):
    d=decision('news','daily','schedule',datetime(2026,10,day,10,tzinfo=timezone.utc))
    due=datetime.fromisoformat(d['due'].replace('Z','+00:00')).astimezone(ZoneInfo('Africa/Cairo'))
    self.assertEqual((due.hour,due.minute,due.second),(17,0,0))
 def test_url_aliases_cannot_bypass_source_deduplication(self):
  self.assertEqual(e.canonical('https://science.nasa.gov/moon/?campaign=1#top'),e.canonical('https://science.nasa.gov/moon'))
  with self.assertRaises(ValueError):e.canonical('https://science.nasa.gov.attacker.example/moon')
 def test_reserved_slot_reuses_its_story_without_new_provider_calls(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'state.json';story={'title':'مصدر جديد','topic_key':'one'}
   state.write_text(json.dumps({'version':2,'episodes':[{'slot':'daily-one','status':'reserved','story':story}]}))
   with patch.object(e,'STATE',state),patch.object(e,'ROOT',root),patch.object(e,'ask',side_effect=AssertionError('must not ask twice')):
    self.assertEqual(e.prepare('science','daily-one'),story)
 def test_a_scheduled_daily_slot_cannot_create_another_episode(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);state=root/'state.json';state.write_text(json.dumps({'version':2,'episodes':[{'slot':'one','status':'scheduled'}]}))
   with patch.object(e,'STATE',state),patch.object(e,'ROOT',root):
    with self.assertRaisesRegex(RuntimeError,'confirmed'):e.prepare('science','one')
 def test_approval_requires_actual_sample_hash(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'release.json';p.write_text(json.dumps({'style_approved':True,'publication_approved':True}))
   with patch('professional_motion.publisher.POLICY',p):self.assertFalse(approved())

if __name__=='__main__':unittest.main()
