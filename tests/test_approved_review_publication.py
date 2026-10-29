import hashlib,json,tempfile,unittest
from pathlib import Path
from professional_motion.publish_approved_review import validate
class ApprovedReviewTests(unittest.TestCase):
 def test_approval_binds_exact_video_and_original_story(self):
  with tempfile.TemporaryDirectory() as td:
   video=Path(td)/'v.mp4';video.write_bytes(b'approved film');story=b'{"topic":"eclipse"}'
   grant={'approved':True,'profile':'science','video_sha256':hashlib.sha256(video.read_bytes()).hexdigest()}
   report={'story_sha256':hashlib.sha256(story).hexdigest(),'topic_key':'solar-eclipse','profile':'science','duration':135.52,'audio_tail':{'audio_tail_checked':True},'visual_gate':{'passed':True}}
   self.assertEqual(validate(grant,video,report,story),grant['video_sha256'])
   for changed in ({**grant,'approved':False},{**grant,'profile':'news'}):
    with self.assertRaises(PermissionError):validate(changed,video,report,story)
   for changed in ({**report,'topic_key':'moon'},{**report,'duration':90},{**report,'audio_tail':{}},{**report,'story_sha256':'0'*64}):
    with self.assertRaises(ValueError):validate(grant,video,changed,story)
   video.write_bytes(b'replacement')
   with self.assertRaises(ValueError):validate(grant,video,report,story)
 def test_scoped_permission_does_not_enable_daily_publication(self):
  self.assertFalse(json.loads(Path('config/professional_release.json').read_text())['publication_approved'])
