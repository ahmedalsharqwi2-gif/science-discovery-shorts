import json,unittest
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
from remotion_factory.daily import decide

class ExplicitDatePriority(unittest.TestCase):
 def check(self,event_name,args_date,event,expected):
  legacy={'publish_date':'2030-01-04'}
  def read(path,*args,**kwargs):return json.dumps(event if str(path)=='event.json' else legacy)
  with patch.dict('os.environ',{'GITHUB_EVENT_NAME':event_name,'GITHUB_EVENT_PATH':'event.json','GITHUB_RUN_ID':'1'}),patch('remotion_factory.daily.Path.read_text',autospec=True,side_effect=read),patch('remotion_factory.daily.Path.exists',return_value=True),patch('remotion_factory.daily.identity',return_value=('owner/repo','science')),patch('remotion_factory.daily.api',return_value={'created_at':'2030-01-03T07:00:00Z'}),patch('remotion_factory.daily.slot_for',return_value=datetime(2030,1,3,15,tzinfo=timezone.utc)) as slot,patch('remotion_factory.daily.destinations',return_value={}),patch('remotion_factory.daily.mutate') as mutate:
   result=decide(SimpleNamespace(date=args_date,dry_run=True))
   self.assertEqual(slot.call_args.args[3],expected);self.assertFalse(result['run']);mutate.assert_not_called()
 def test_explicit_cli_date_wins_over_old_push_marker(self):self.check('push','2030-01-03',{},'2030-01-03')
 def test_explicit_dispatch_input_wins_over_old_push_marker(self):self.check('push',None,{'inputs':{'publish_date':'2030-01-03'}},'2030-01-03')
 def test_manual_marker_is_used_only_without_an_explicit_target(self):self.check('push',None,{},'2030-01-04')
 def test_clock_event_ignores_old_manual_marker(self):self.check('schedule',None,{'schedule':'0 7 * * *'},None)
