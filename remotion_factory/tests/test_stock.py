import unittest
from unittest.mock import patch
from remotion_factory.stock import verify_occupied
from remotion_factory.health import AuditFailure

class OccupiedSlot(unittest.TestCase):
 def verify(self,**overrides):
  values={'check_posts':({'youtube':{'id':'p'}},'https://github.com/own/repo/releases/download/full/movie.mp4'),'episode_for':{'expected_sha256':'original'},'original_release_url':'https://github.com/own/repo/releases/download/full/movie.mp4','verify_media':{'passed':True,'duration':119.6}}
  values.update(overrides)
  from contextlib import ExitStack
  with ExitStack() as stack:
   mocks={}
   for name,value in values.items():mocks[name]=stack.enter_context(patch('remotion_factory.stock.'+name,side_effect=value if isinstance(value,Exception) else None,return_value=None if isinstance(value,Exception) else value))
   return verify_occupied('stickman',{}, {},'2026-11-03T15:00:00Z'),mocks
 def test_verified_retained_full_film_is_preserved_without_generation(self):
  result,mocks=self.verify();self.assertTrue(result['technical_passed']);self.assertEqual(result['video_sha256'],'original');self.assertEqual(mocks['episode_for'].call_args.args[2],{'youtube':{'id':'p'}})
 def test_replaced_post_ids_do_not_silently_count_as_success(self):
  with self.assertRaises(AuditFailure):self.verify(episode_for=AuditFailure('Receipt IDs do not match'))
 def test_external_replacement_url_is_rejected(self):
  with self.assertRaises(AuditFailure):self.verify(original_release_url='https://github.com/own/repo/releases/download/other/movie.mp4')
 def test_short_or_corrupt_video_is_rejected(self):
  with self.assertRaises(AuditFailure):self.verify(verify_media=AuditFailure('Permanent measured-duration rule failed'))
