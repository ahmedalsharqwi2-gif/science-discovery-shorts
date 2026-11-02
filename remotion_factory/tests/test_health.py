import copy,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from remotion_factory.health import check_posts,schedule_allowed,target_due,AuditFailure,alert,episode_for
class AuditTests(unittest.TestCase):
 def setUp(self):
  self.due=target_due(datetime(2026,11,4).date());self.mapping={s:{'channel':s} for s in ('youtube','facebook','instagram')};self.rows={s:[{'id':s+'-post','channelId':s,'dueAt':'2026-11-04T15:00:00Z','status':'scheduled','assets':[{'source':'https://github.com/owner/repo/releases/download/production/video.mp4'}]}] for s in self.mapping}
 def test_three_actual_ids_same_video_and_exact_cairo17(self):
  receipts,url=check_posts(self.mapping,self.rows,self.due,'prepublish');self.assertEqual(len(receipts),3);self.assertTrue(url.endswith('/video.mp4'))
 def test_missing_destination_cannot_be_success(self):
  self.rows['instagram']=[]
  with self.assertRaises(AuditFailure):check_posts(self.mapping,self.rows,self.due,'prepublish')
 def test_duplicate_same_destination_detected(self):
  self.rows['youtube']*=2
  with self.assertRaises(AuditFailure):check_posts(self.mapping,self.rows,self.due,'prepublish')
 def test_wrong_time_or_channel_or_media_is_rejected(self):
  for key,value in [('dueAt','2026-11-04T14:00:00Z'),('channelId','wrong'),('assets',[{'source':'another-film'}])]:
   rows=copy.deepcopy(self.rows);rows['facebook'][0][key]=value
   with self.assertRaises(AuditFailure):check_posts(self.mapping,rows,self.due,'prepublish')
 def test_scheduled_is_not_evidence_of_successful_publication(self):
  with self.assertRaises(AuditFailure):check_posts(self.mapping,self.rows,self.due,'postpublish')
 def test_postpublish_needs_live_sent_state_and_external_link(self):
  for s in self.rows:self.rows[s][0].update(status='sent',sentAt='2026-11-04T15:00:10Z',externalLink='https://example.org/published/'+s)
  self.assertEqual(len(check_posts(self.mapping,self.rows,self.due,'postpublish')[0]),3)
  self.rows['youtube'][0]['externalLink']=None
  with self.assertRaises(AuditFailure):check_posts(self.mapping,self.rows,self.due,'postpublish')
 def test_platform_copies_after_publication_are_bound_to_original_post_ids(self):
  for s in self.rows:self.rows[s][0].update(status='sent',sentAt='2026-11-04T15:00:10Z',externalLink='https://example.org/'+s,assets=[{'source':'https://media.example.org/'+s+'.mp4'}])
  receipts,url=check_posts(self.mapping,self.rows,self.due,'postpublish');self.assertIsNone(url)
  episode={'due_at':'2026-11-04T15:00:00Z','video_sha256':'a'*64,'receipts':{s:{'id':r['id']} for s,r in receipts.items()}}
  with patch('remotion_factory.health.read_json',side_effect=lambda path,default=None:{'episodes':{'slot':episode}} if 'remotion_registry' in path else default):
   self.assertEqual(episode_for(self.due.date(),None,receipts)['expected_sha256'],'a'*64)
   changed=copy.deepcopy(receipts);changed['youtube']['id']='another-post'
   with self.assertRaises(AuditFailure):episode_for(self.due.date(),None,changed)
 def test_cairo_winter_checkpoint_and_wrong_dst_trigger(self):
  now=datetime(2026,11,4,9,35,tzinfo=timezone.utc)
  self.assertTrue(schedule_allowed(now,'30 9 * * *'));self.assertFalse(schedule_allowed(now,'30 8 * * *'))
 def test_cairo_summer_checkpoint(self):
  now=datetime(2026,7,4,8,35,tzinfo=timezone.utc)
  self.assertTrue(schedule_allowed(now,'30 8 * * *'));self.assertFalse(schedule_allowed(now,'30 9 * * *'))
 @patch('remotion_factory.health.identity',return_value=('ahmedalsharqwi2-gif/science-discovery-shorts','science'))
 @patch('remotion_factory.health.gh')
 def test_failure_opens_one_own_repo_issue(self,gh,identity):
  gh.side_effect=[[],{'number':1}]
  alert({'date':'2026-11-04','phase':'prepublish','passed':False,'errors':['Missing film'],'run_url':'https://github.com/owner/repo/actions/runs/1','report_path':'reviews/check.json'})
  self.assertEqual(gh.call_args.args[:2],('/issues','POST'));self.assertIn('Missing film',gh.call_args.args[2]['body'])
if __name__=='__main__':unittest.main()
