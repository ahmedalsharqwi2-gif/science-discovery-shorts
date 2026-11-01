import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
from production_v2.release_media import ReviewReleaseUploader

class ReviewReleaseTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.video=Path(self.temp.name)/'test-only.mp4';self.video.write_bytes(b'mocked media bytes for HTTP contract test only')
  self.env=patch.dict('os.environ',{'GITHUB_TOKEN':'test-token','GITHUB_REPOSITORY':'owner/repo','GITHUB_SHA':'a'*40,'PRODUCTION_MEDIA_ID':'v2-review-test'})
  self.env.start();self.addCleanup(self.env.stop)
 def response(self,status,data):
  result=Mock(status_code=status);result.json.return_value=data;result.text='mock response';return result
 def test_review_release_has_no_social_publication_description(self):
  release={'upload_url':'https://uploads.github.com/repos/owner/repo/releases/1/assets{?name,label}','assets':[]}
  upload={'browser_download_url':'https://github.com/owner/repo/releases/download/review-v2-review-test/review.mp4'}
  with patch('production_v2.release_media.requests.get',return_value=self.response(404,{})),patch('production_v2.release_media.requests.post',side_effect=[self.response(201,release),self.response(201,upload)]) as post:
   url=ReviewReleaseUploader()._release_asset_url(self.video)
  self.assertEqual(url,upload['browser_download_url'])
  body=post.call_args_list[0].kwargs['json'];self.assertEqual(body['tag_name'],'review-v2-review-test')
  self.assertIn('Not scheduled or published to social accounts',body['body'])
  self.assertTrue(body['prerelease'])
 def test_matching_existing_review_asset_is_reused_without_reupload(self):
  digest=hashlib.sha256(self.video.read_bytes()).hexdigest()
  asset={'name':'review-video-v2-review-test.mp4','digest':'sha256:'+digest,'browser_download_url':'https://github.com/owner/repo/existing.mp4'}
  with patch('production_v2.release_media.requests.get',return_value=self.response(200,{'assets':[asset]})),patch('production_v2.release_media.requests.post') as post:
   self.assertEqual(ReviewReleaseUploader()._release_asset_url(self.video),asset['browser_download_url'])
   post.assert_not_called()
 def test_existing_changed_asset_is_never_replaced(self):
  asset={'name':'review-video-v2-review-test.mp4','digest':'sha256:'+'b'*64,'browser_download_url':'https://github.com/owner/repo/existing.mp4'}
  with patch('production_v2.release_media.requests.get',return_value=self.response(200,{'assets':[asset]})),patch('production_v2.release_media.requests.post') as post:
   with self.assertRaises(RuntimeError):ReviewReleaseUploader()._release_asset_url(self.video)
   post.assert_not_called()

if __name__=='__main__':unittest.main()
