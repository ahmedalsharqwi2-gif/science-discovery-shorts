import os,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
from voice_provider.client import generate,config
class AcceptedVoiceTests(unittest.TestCase):
    def test_approved_settings(self):
        c=config();self.assertEqual((c['provider'],c['speaker'],c['speed'],c['num_step']),('voicetut','Mohammed',1,32));self.assertFalse(c['fallback_allowed'])
    def test_empty_text_stops_before_a_provider(self):
        with self.assertRaisesRegex(ValueError,'empty'):generate('   ',Path('output/unused.mp3'))
    def test_missing_runtime_never_selects_another_voice(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'VOICETUT_PYTHON':''}):
            with self.assertRaisesRegex(RuntimeError,'No replacement voice'):generate('ده نص مصري جديد للاختبار.',Path(tmp)/'voice.mp3')
