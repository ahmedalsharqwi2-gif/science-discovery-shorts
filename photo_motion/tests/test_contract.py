import copy, hashlib, json, os, tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from photo_motion.contract import validate
from photo_motion.engine import Renderer,render
from photo_motion.bridge import render_if_requested

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        im=Image.new('RGB',(1080,1920),'#1c3946');im.save(self.root/'picture.png')
        with wave.open(str(self.root/'voice.wav'),'wb') as f:
            f.setnchannels(1);f.setsampwidth(2);f.setframerate(48000)
            audio=(np.sin(np.arange(57600)*2*np.pi*220/48000)*6000).astype(np.int16);f.writeframes(audio.tobytes())
        self.data={'schema_version':1,'profile':'history','duration':1.2,'audio':{'path':'voice.wav','speed':1,'pitch_semitones':0,'provenance':'synthetic tone for a technical test only'},'review':{k:{'approved':True,'by':'test fixture'} for k in ('script','voice','images','caption_timing')},'asset_sha256':{x:hashlib.sha256((self.root/x).read_bytes()).hexdigest() for x in ('picture.png','voice.wav')},'scenes':[{'start':0,'end':1.2,'background':'picture.png','subject':'technical fixture','visual_rationale':'test contract','title':'اختبار'}],'captions':[{'start':0,'end':1.2,'text':'اختبار النص العربي'}],'narration_text':'اختبار النص العربي'}
    def tearDown(self):self.tmp.cleanup()
    def manifest(self):
        p=self.root/'episode.json';p.write_text(json.dumps(self.data));return p
    def test_valid_and_deterministic(self):
        r=Renderer(self.manifest());self.assertEqual(r.frame(.5).tobytes(),r.frame(.5).tobytes())
    def test_channel_profiles_render_safe_arabic(self):
        for profile in ('history','science','horror'):
            self.data['profile']=profile
            r=Renderer(self.manifest())
            self.assertEqual(r.frame(.5).size,(1080,1920))
    def test_missing_voice_approval_is_rejected(self):
        self.data['review']['voice']['approved']=False
        with self.assertRaisesRegex(ValueError,'review'):validate(self.manifest())
    def test_replaced_asset_is_rejected(self):
        (self.root/'picture.png').write_bytes(b'replaced')
        with self.assertRaisesRegex(ValueError,'reviewed version'):validate(self.manifest())
    def test_voice_speed_change_is_rejected(self):
        self.data['audio']['speed']=.8
        with self.assertRaisesRegex(ValueError,'speed'):validate(self.manifest())
    def test_narration_cutoff_is_rejected(self):
        self.data['duration']=.8
        with self.assertRaisesRegex(ValueError,'entire'):validate(self.manifest())
    def test_storyboard_gap_is_rejected(self):
        self.data['scenes'][0]['start']=.2
        with self.assertRaisesRegex(ValueError,'gaps'):validate(self.manifest())
    def test_caption_overflow_is_rejected(self):
        self.data['captions'][0]['text']=' '.join(['كلمة']*100)
        with self.assertRaisesRegex(ValueError,'three safe rows'):Renderer(self.manifest())
    def test_mismatched_episode_cannot_reuse_voice(self):
        with patch.dict(os.environ,{'PHOTO_MOTION_MANIFEST':str(self.manifest())}):
            with self.assertRaisesRegex(ValueError,'script'):render_if_requested(self.root/'voice.wav','قصة أخرى',self.root/'wrong.mp4','history')
    def test_mp4_export_preserves_full_audio(self):
        out=render(self.manifest(),self.root/'check.mp4')
        report=json.loads(out.with_suffix('.verification.json').read_text())
        self.assertTrue(report['full_narration_preserved']);self.assertGreater(report['voice_pcm_correlation'],.98)
if __name__=='__main__':unittest.main()
