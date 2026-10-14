import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from arabic_tts_quality_checker import ArabicTTSQualityChecker

class ASRVerificationRecoveryTests(unittest.TestCase):
    def check(self, accurate):
        calls = []
        expected = 'هذه تجربة عربية واضحة لفحص سلامة الصوت'
        class Model:
            def __init__(self, name, **kwargs): self.name = name; calls.append(name)
            def transcribe(self, path, **kwargs):
                if 'initial_prompt' in kwargs: raise AssertionError('Script must not be supplied to ASR')
                text = expected if accurate and self.name == 'small' else 'كلمات مختلفة تماما'
                return [types.SimpleNamespace(text=text)], None
        modules = {'faster_whisper': types.SimpleNamespace(WhisperModel=Model),
                   'scipy': types.ModuleType('scipy'),
                   'scipy.io': types.SimpleNamespace(wavfile=object())}
        with patch.dict(sys.modules, modules), patch.dict('os.environ', {'WHISPER_MODEL':'base','ASR_VERIFY_MODEL':'small'}), patch.object(Path, 'exists', return_value=True), patch('arabic_tts_quality_checker.subprocess.run', return_value=types.SimpleNamespace(stdout='4.375')):
            score, issues = ArabicTTSQualityChecker().check_audio_quality(Path('audio.mp3'), expected)
        self.assertEqual(calls, ['base', 'small'])
        return score, issues
    def test_independent_accurate_verifier_recovers_base_false_rejection(self):
        score, issues = self.check(True)
        self.assertEqual(issues, [])
        self.assertEqual(score, 1.0)
    def test_missing_speech_still_blocks_after_second_verifier(self):
        score, issues = self.check(False)
        self.assertTrue(any('تطابق' in issue for issue in issues))
        self.assertLess(score, 1.0)
