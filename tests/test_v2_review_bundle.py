import hashlib
import json
import tempfile
import unittest
import wave
from pathlib import Path
from production_v2.review import bundle

class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.story = {'profile':'science','topic_key':'archived-science-test','scenes':[{'id':str(i)} for i in range(8)]}
        self.root.joinpath('story.json').write_text(json.dumps(self.story))
        with wave.open(str(self.root / 'narration.wav'),'wb') as audio:
            audio.setparams((1, 2, 100, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 12000)
        self.timing = {'duration':120,'coverage':1,'topic_key':self.story['topic_key'],
                       'scenes':[{'id':str(i),'start':i*15,'end':(i+1)*15} for i in range(8)],
                       'story_sha256':hashlib.sha256((self.root/'story.json').read_bytes()).hexdigest(),
                       'audio_sha256':hashlib.sha256((self.root/'narration.wav').read_bytes()).hexdigest()}
        self.save()
    def save(self):
        (self.root/'timing.json').write_text(json.dumps(self.timing))
    def test_complete_matched_bundle(self):
        self.assertEqual(bundle(self.root,'science')[1]['duration'],120)
    def test_modified_voice_rejected(self):
        with (self.root/'narration.wav').open('ab') as stream: stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'): bundle(self.root,'science')
    def test_wrong_channel_rejected(self):
        with self.assertRaisesRegex(ValueError,'another channel'): bundle(self.root,'news')
    def test_unmeasured_or_short_bundle_rejected(self):
        for field,value in [('coverage',.2),('duration',119.9),('duration',float('nan')),('topic_key','other')]:
            old = self.timing[field]; self.timing[field]=value; self.save()
            with self.assertRaises(ValueError): bundle(self.root,'science')
            self.timing[field]=old
    def test_nonfinite_scene_timing_or_mismatched_identity_rejected(self):
        for field,value in [('start',float('nan')),('end',float('inf')),('id','other')]:
            old=self.timing['scenes'][3][field];self.timing['scenes'][3][field]=value;self.save()
            with self.assertRaises(ValueError):bundle(self.root,'science')
            self.timing['scenes'][3][field]=old

    def test_missing_scene_or_unordered_timing_rejected(self):
        self.timing['scenes'][1]['start']=0;self.save()
        with self.assertRaisesRegex(ValueError,'unordered'):bundle(self.root,'science')

if __name__=='__main__':unittest.main()
