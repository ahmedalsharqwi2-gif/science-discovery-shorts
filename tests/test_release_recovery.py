import ast
import importlib.util
import os
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]

class Repairs(unittest.TestCase):
    def publisher(self):
        spec = importlib.util.spec_from_file_location("publisher", ROOT / "scripts/publish_content.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_release_creation_sets_valid_tag_and_explicit_commit(self):
        module = self.publisher()
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"; video.write_bytes(b"video")
            with patch.dict(os.environ, {"GITHUB_TOKEN": "test", "GITHUB_REPOSITORY": "owner/repo",
                                         "PRODUCTION_MEDIA_ID": "38358457130--", "GITHUB_SHA": "a"*40}):
                publisher = module.ContentPublisher()
                created = Mock(status_code=201)
                created.json.return_value = {"assets": [{"name": "science-video-38358457130--.mp4",
                                                         "browser_download_url": "https://example.test/video.mp4"}]}
                with patch.object(module.requests, "get", return_value=Mock(status_code=404)), patch.object(module.requests, "post", return_value=created) as post:
                    self.assertEqual(publisher._release_asset_url(video), "https://example.test/video.mp4")
                    payload = post.call_args.kwargs["json"]
                    self.assertEqual(payload["target_commitish"], "a"*40)
                    self.assertEqual(payload["tag_name"], "auto-publish-38358457130")

    def test_release_422_cannot_be_mistaken_for_success(self):
        module = self.publisher()
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / "video.mp4"; video.write_bytes(b"video")
            p = module.ContentPublisher(); p.github_token="test"; p.repository="owner/repo"
            with patch.object(module.requests, "get", return_value=Mock(status_code=404)), patch.object(module.requests, "post", return_value=Mock(status_code=422, text="invalid target")):
                with self.assertRaises(RuntimeError): p._release_asset_url(video)

if __name__ == "__main__": unittest.main()
