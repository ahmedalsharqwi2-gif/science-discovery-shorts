import copy,unittest
from scripts.reschedule_existing import retime
OLD='2026-11-03T15:00:00Z';NEW='2026-11-02T15:00:00Z'
class RetimeTests(unittest.TestCase):
 def setUp(self):
  self.post={'id':'existing','channelId':'channel','status':'scheduled','dueAt':OLD,'text':'unchanged title','assets':[{'source':'same-movie.mp4'}],'shareMode':'customScheduled','schedulingType':'automatic'}
  self.item={'id':'existing','channel_id':'channel'};self.progress={};self.edits=[];self.checkpoints=[]
 def read(self,id):return copy.deepcopy(self.post)
 def checkpoint(self):self.checkpoints.append(copy.deepcopy(self.progress))
 def edit(self,id,due):
  assert self.checkpoints[-1]['phase']=='intent'
  self.edits.append((id,due));self.post['dueAt']=due;return {'id':id,'dueAt':due}
 def run_case(self):return retime(self.item,OLD,NEW,self.progress,self.read,self.edit,self.checkpoint)
 def test_edits_same_id_only_after_durable_intent_and_keeps_media(self):
  original=copy.deepcopy(self.post);result=self.run_case()
  self.assertEqual(self.edits,[('existing',NEW)]);self.assertEqual(result['assets'],original['assets']);self.assertEqual(self.progress['phase'],'verified')
 def test_already_moved_post_is_reconciled_without_mutation(self):
  self.post['dueAt']=NEW;self.run_case();self.assertEqual(self.edits,[])
 def test_wrong_channel_never_mutates(self):
  self.post['channelId']='other'
  with self.assertRaises(ValueError):self.run_case()
  self.assertEqual(self.edits,[])
 def test_sent_post_never_mutates(self):
  self.post['status']='sent'
  with self.assertRaises(ValueError):self.run_case()
  self.assertEqual(self.edits,[])
 def test_uncertain_previous_edit_is_not_repeated(self):
  self.progress={'phase':'uncertain','before':copy.deepcopy(self.post)}
  with self.assertRaises(ValueError):self.run_case()
  self.assertEqual(self.edits,[])
 def test_accepted_but_timed_out_edit_is_reconciled_by_id(self):
  self.progress={'phase':'uncertain','before':copy.deepcopy(self.post)};self.post['dueAt']=NEW
  self.run_case();self.assertEqual(self.edits,[]);self.assertEqual(self.progress['phase'],'verified')
 def test_media_change_is_rejected(self):
  self.progress={'before':copy.deepcopy(self.post)};self.post['assets']=[{'source':'different.mp4'}]
  with self.assertRaises(ValueError):self.run_case()
  self.assertEqual(self.edits,[])
if __name__=='__main__':unittest.main()
