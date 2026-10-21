import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image
from scripts.pollinations_images import generated_illustration


class PollinationsImagesTests(unittest.TestCase):
    def reply(self, data, status=200, content_type='image/jpeg'):
        response = MagicMock()
        response.status_code = status
        response.headers = {'Content-Type': content_type}
        response.iter_content.return_value = [data]
        response.__enter__.return_value = response
        return response

    def test_valid_image_is_cached_and_does_not_generate_again(self):
        data = io.BytesIO()
        Image.new('RGB', (580, 1015), '#236071').save(data, format='JPEG')
        with tempfile.TemporaryDirectory() as folder, patch(
            'scripts.pollinations_images.requests.get', return_value=self.reply(data.getvalue())
        ) as request:
            a=generated_illustration({'prompt':'A propeller hub'}, Path(folder))
            b=generated_illustration({'prompt':'A propeller hub'}, Path(folder))
            self.assertFalse(a['cached'])
            self.assertTrue(b['cached'])
            self.assertEqual(a['source_width'],580)
            self.assertFalse(a['paid_fallback_used'])
            self.assertEqual(request.call_count,1)

    def test_html_error_page_never_becomes_a_scene(self):
        with tempfile.TemporaryDirectory() as folder, patch(
            'scripts.pollinations_images.requests.get', return_value=self.reply(b'<html>Error</html>', content_type='text/html')
        ):
            with self.assertRaisesRegex(RuntimeError,'non-image'):
                generated_illustration({'prompt':'A propeller hub'}, Path(folder))
            self.assertFalse(list(Path(folder).rglob('*.jpg')))
