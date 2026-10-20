import unittest
from datetime import datetime,timezone
from scripts.daily_schedule import next_slot,validate_slot
class DailyScheduleTests(unittest.TestCase):
 def test_summer_is_14_utc(self):self.assertEqual(next_slot(datetime(2026,10,21,10,tzinfo=timezone.utc)).isoformat(),'2026-10-21T14:00:00+00:00')
 def test_winter_is_15_utc(self):self.assertEqual(next_slot(datetime(2026,11,21,10,tzinfo=timezone.utc)).isoformat(),'2026-11-21T15:00:00+00:00')
 def test_after_cutoff_uses_next_day_not_immediate(self):self.assertEqual(next_slot(datetime(2026,10,21,15,tzinfo=timezone.utc)).isoformat(),'2026-10-22T14:00:00+00:00')
 def test_dst_weekend_keeps_local_hour(self):
  from zoneinfo import ZoneInfo
  for day in [28,29,30,31]:
   self.assertEqual(next_slot(datetime(2026,10,day,10,tzinfo=timezone.utc)).astimezone(ZoneInfo('Africa/Cairo')).hour,17)
 def test_wrong_hour_and_past_are_rejected(self):
  now=datetime(2026,10,21,10,tzinfo=timezone.utc)
  for due in ['2026-10-21T13:00:00Z','2026-10-20T14:00:00Z']:
   with self.assertRaises(ValueError):validate_slot(due,now)
 def test_confirmed_slot_skips_only_after_all_receipts(self):
  import tempfile,os,json
  from pathlib import Path
  from unittest.mock import patch
  from scripts.daily_schedule import plan
  due=datetime(2026,10,21,14,tzinfo=timezone.utc)
  key='stock 2026-10-21 17 Cairo'
  with tempfile.TemporaryDirectory() as directory:
   previous=os.getcwd()
   try:
    os.chdir(directory);Path('state').mkdir()
    output=Path(directory)/'output';envfile=Path(directory)/'env'
    entry={'confirmed':True,'required_services':['youtube','facebook'],'receipts':{'youtube':{'id':'yt-real'}}}
    with patch('scripts.daily_schedule.next_slot',return_value=due),patch.dict(os.environ,{'GITHUB_OUTPUT':str(output),'GITHUB_ENV':str(envfile)}):
     Path('state/publication_stock.json').write_text(json.dumps({'slots':{key:entry}}))
     plan();self.assertIn('already_confirmed=false',output.read_text())
     entry['receipts']['facebook']={'id':'buffer-real'}
     Path('state/publication_stock.json').write_text(json.dumps({'slots':{key:entry}}))
     output.write_text('');plan();self.assertIn('already_confirmed=true',output.read_text())
   finally:os.chdir(previous)
if __name__=='__main__':unittest.main()
