import base64,io,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from news.images import prepare_images,decoded_image

class Reply:
    status_code=200
    headers={'Content-Type':'application/json'}
    def json(self):
        b=io.BytesIO();Image.new('RGB',(1024,1024),(54,80,110)).save(b,'JPEG')
        return {'success':True,'result':{'image':base64.b64encode(b.getvalue()).decode()}}

class ImagesTests(unittest.TestCase):
    def test_resume_reuses_images_without_another_request(self):
        with tempfile.TemporaryDirectory() as td:
            old=os.getcwd()
            try:
                os.chdir(td)
                with patch.dict(os.environ,{'CLOUDFLARE_API_TOKEN':'fake-test','CLOUDFLARE_ACCOUNT_ID':'a'*32}),patch('news.images.photo_prompts',return_value=['a photographic laboratory '+('details '*20)]),patch('news.images.requests.post',return_value=Reply()) as call:
                    plan={'source':{'url':'https://blogs.nvidia.com/example'}}
                    first=prepare_images(plan);second=prepare_images(plan)
                    self.assertEqual(call.call_count,1)
                    self.assertEqual(first[0].read_bytes(),second[0].read_bytes())
                    self.assertTrue(json.loads(Path('output/image_manifest.json').read_text())['images'][0]['cache_hit'])
            finally:os.chdir(old)
    def test_permission_error_stops_without_leaking_provider_payload(self):
        r=Reply();r.status_code=403
        with self.assertRaisesRegex(RuntimeError,'HTTP 403'):decoded_image(r)
    def test_success_without_image_is_rejected(self):
        r=Reply()
        with patch.object(r,'json',return_value={'success':True,'result':{'text':'no image'}}):
            with self.assertRaisesRegex(ValueError,'no image'):decoded_image(r)
