import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from scripts.commons_media import search_images, image_fallback, animate_image

class CommonsTests(unittest.TestCase):
    @patch("scripts.commons_media.requests.get")
    def test_license_and_host_filter(self, get):
        def page(i, license, host="upload.wikimedia.org"):
            return {"pageid": i, "imageinfo": [{"mime": "image/jpeg", "url": "https://"+host+"/test.jpg",
                "extmetadata": {"LicenseShortName": {"value": license}}}]}
        get.return_value.json.return_value={"query":{"pages":{"1":page(1,"CC0"),"2":page(2,"CC BY-SA 4.0"),
            "3":page(3,"Public domain"),"4":page(4,"CC0","example.com")}}}
        self.assertEqual([x["id"] for x in search_images("map")], ["commons_1","commons_3"])

    @patch("scripts.commons_media.animate_image")
    @patch("scripts.commons_media.requests.get")
    @patch("scripts.commons_media.search_images")
    def test_rejected_bytes_never_enter_manifest(self, search, get, animate):
        search.return_value=[{"id":"commons_1","url":"https://upload.wikimedia.org/a.jpg"}]
        response=Mock();response.iter_content.return_value=[b"image"]
        get.return_value.__enter__.return_value=response
        animate.side_effect=lambda source,dest,**kw:dest.write_bytes(b"video")
        with tempfile.TemporaryDirectory() as d:
            reviewer=Mock(side_effect=ValueError("wrong era"))
            self.assertEqual(image_fallback("map","topic",Path(d),reviewer,historical=True),[])
            self.assertFalse(list(Path(d).glob("*.mp4")))
            reviewer.assert_called_once()

    @patch("scripts.commons_media.animate_image")
    @patch("scripts.commons_media.requests.get")
    @patch("scripts.commons_media.search_images")
    def test_approved_asset_keeps_source_metadata(self, search, get, animate):
        search.return_value=[{"id":"commons_1","url":"https://upload.wikimedia.org/a.jpg","license":"CC0"}]
        response=Mock();response.iter_content.return_value=[b"image"]
        get.return_value.__enter__.return_value=response
        animate.side_effect=lambda source,dest,**kw:dest.write_bytes(b"video")
        with tempfile.TemporaryDirectory() as d:
            result=image_fallback("map","topic",Path(d),Mock(return_value={"status":"PASS"}))
            self.assertEqual(result[0]["license"],"CC0")
            self.assertTrue(list(Path(d).glob("*.source.json")))
