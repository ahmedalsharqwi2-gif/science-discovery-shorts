import importlib.util
import math
import tempfile
import unittest
import wave
from array import array
from pathlib import Path

spec = importlib.util.spec_from_file_location('voice', Path(__file__).resolve().parents[1] / 'scripts/free_tts_fallback.py')
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)

class ContinuityTests(unittest.TestCase):
    def test_keeps_words_and_diacritics(self):
        text = 'هَلْ تَعْلَمُ كَيْفَ تَحَوَّلَتْ مَدِينَةُ سِينْ-پِييْرَ؟ ' * 8
        tokens = voice.narration_tokens(text)
        self.assertEqual(' '.join(tokens).split(), text.split())
        self.assertTrue(all(len(t) <= 100 for t in tokens))
        self.assertTrue(all('سِينْ' not in t or 'سِينْ-پِييْرَ' in t for t in tokens))

    def test_prefers_clause_boundary(self):
        text = 'هذه جملة كاملة، وهذه تفاصيل إضافية ' * 5
        self.assertTrue(voice.narration_tokens(text)[0].endswith('،'))

    def test_no_decimal_split(self):
        text = 'القيمة 10.5 والوقت 12:30 والاسم سين-بيير ' * 5
        self.assertEqual(' '.join(voice.narration_tokens(text)).split(), text.split())

    def test_rejects_oversized_word_instead_of_cutting_it(self):
        with self.assertRaises(ValueError): voice.narration_tokens('س' * 101)

    def test_silence_guard_preserves_all_speech_and_internal_pause(self):
        tone = [int(1000 * math.sin(i / 10)) for i in range(2400)]
        data = [0] * 12000 + tone + [0] * 6000 + tone + [0] * 12000
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'part.wav'
            with wave.open(str(p), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
                w.writeframes(array('h', data).tobytes())
            trimmed = array('h', voice._boundary_pcm(p))
            self.assertEqual([x for x in trimmed if x], [x for x in data if x])
            self.assertIn(array('h', tone + [0]*6000 + tone).tobytes(), trimmed.tobytes())
            self.assertLess(len(trimmed), len(data))

    def test_silent_provider_response_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'part.wav'
            with wave.open(str(p), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000)
                w.writeframes(b'\0' * 48000)
            with self.assertRaises(RuntimeError): voice._boundary_pcm(p)

if __name__ == '__main__': unittest.main()
