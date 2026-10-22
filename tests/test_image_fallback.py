import os
import unittest
from unittest.mock import patch
from PIL import Image
from film_factory import image_fallback as f

class ImageFallbackTests(unittest.TestCase):
    def test_unapproved_domains_blocked(self):
        with self.assertRaises(ValueError):
            f._get_image("https://not-example.com/photo.jpg")
    def test_opt_out_blocks_network(self):
        with patch.dict(os.environ,{"FILM_ALLOW_STOCK_FALLBACK":"0"}):
            with patch.object(f,"pexels") as p:
                self.assertIsNone(f.fallback("cat",None))
                p.assert_not_called()
    def test_pexels_optional_then_public_domain(self):
        with patch.dict(os.environ,{"FILM_ALLOW_STOCK_FALLBACK":"1"}):
            with patch.object(f,"pexels",return_value=None) as p,patch.object(f,"commons",return_value=(Image.new("RGB",(1080,1920)),{"provider":"Wikimedia Commons","license":"cc0"})) as c:
                img,meta=f.fallback("scientific cells",None)
                self.assertEqual(img.size,(1080,1920))
                self.assertEqual(meta["license"],"cc0")
                p.assert_called_once();c.assert_called_once()
    def test_no_provider_does_not_invent_image(self):
        with patch.dict(os.environ,{"FILM_ALLOW_STOCK_FALLBACK":"1"}):
            with patch.object(f,"pexels",return_value=None),patch.object(f,"commons",return_value=None):
                self.assertIsNone(f.fallback("specific unavailable subject",None))
if __name__=="__main__":unittest.main()
