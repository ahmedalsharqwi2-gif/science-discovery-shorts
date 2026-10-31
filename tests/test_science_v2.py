"""Fail closed before mixing when isolated v2 evidence is inconsistent."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from professional_motion import finish


class IsolatedScienceV2Tests(unittest.TestCase):
    def fixture(self, root, duration=150, pipeline='v2'):
        delivery=root/'isolated-delivery';output=root/'isolated-render'
        delivery.mkdir();output.mkdir()
        story={'topic_key':'fixture','profile':'science'}
        story_bytes=json.dumps(story).encode();voice=b'test bytes: not playable narration'
        (delivery/'story.json').write_bytes(story_bytes)
        (delivery/'narration.wav').write_bytes(voice)
        story_sha=hashlib.sha256(story_bytes).hexdigest()
        timing={'duration':duration,'topic_key':'fixture','story_sha256':story_sha,
                'audio_sha256':hashlib.sha256(voice).hexdigest()}
        (delivery/'timing.json').write_text(json.dumps(timing))
        (output/'render.json').write_text(json.dumps({'pipeline':pipeline,'story_sha256':story_sha}))
        return delivery,output

    def invoke(self, delivery, output):
        argv=['finish','--pipeline','v2','--delivery-dir',str(delivery),'--output-dir',str(output)]
        with patch.object(sys,'argv',argv),patch.object(finish,'build') as build:
            try:
                finish.main()
            finally:
                build.assert_not_called()

    def test_v2_rejects_short_voice_before_any_audio_mix(self):
        with tempfile.TemporaryDirectory() as folder:
            delivery,output=self.fixture(Path(folder),119.99)
            with self.assertRaisesRegex(ValueError,'120 seconds'):
                self.invoke(delivery,output)
            self.assertFalse((output/'professional-review.mp4').exists())

    def test_legacy_render_cannot_be_used_as_v2_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            delivery,output=self.fixture(Path(folder),pipeline='legacy')
            with self.assertRaisesRegex(ValueError,'pipeline'):
                self.invoke(delivery,output)

    def test_changed_isolated_voice_stops_before_mixing(self):
        with tempfile.TemporaryDirectory() as folder:
            delivery,output=self.fixture(Path(folder))
            (delivery/'narration.wav').write_bytes(b'changed voice')
            with self.assertRaisesRegex(ValueError,'different audio'):
                self.invoke(delivery,output)

    def test_changed_isolated_story_stops_before_mixing(self):
        with tempfile.TemporaryDirectory() as folder:
            delivery,output=self.fixture(Path(folder))
            (delivery/'story.json').write_text(json.dumps({'topic_key':'fixture','profile':'science','changed':True}))
            with self.assertRaisesRegex(ValueError,'Story changed'):
                self.invoke(delivery,output)
