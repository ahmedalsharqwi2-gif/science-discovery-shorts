import base64, io, json, os, tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from voice_provider.client import generate, config
from api_budget import reserve, BudgetExceeded

def wav_bytes():
    b=io.BytesIO()
    with wave.open(b,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(b'\0\x01'*24000)
    return b.getvalue()
class Reply:
    def __enter__(self):return io.BytesIO(json.dumps({'id':'test-only','steps':[{'type':'model_output','content':[{'type':'audio','data':base64.b64encode(wav_bytes()).decode()}]}]}).encode())
    def __exit__(self,*a):pass
class AcceptedVoiceTests(unittest.TestCase):
    def test_approved_settings(self):
        c=config();self.assertEqual((c['model'],c['speaker']),('gemini-3.8-flash-tts','Charon'));self.assertFalse(c['fallback_allowed'])
    def test_empty_stops_without_api(self):
        with self.assertRaisesRegex(ValueError,'empty'):generate(' ',Path('output/unused.mp3'))
    def test_missing_key_does_not_select_replacement(self):
        with patch.dict(os.environ,{'GEMINI_TTS_API_KEY':'','GEMINI_API_KEY':''}):
            with self.assertRaisesRegex(RuntimeError,'No replacement voice'):generate('ده اختبار.',Path('/tmp/unused.wav'))
    def test_cached_narration_never_spends_a_second_request(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder','GEMINI_TTS_API_KEY':'','VOICE_CACHE_DIR':td+'/cache','API_BUDGET_PATH':td+'/budget.sqlite3','GEMINI_TTS_MIN_INTERVAL':'0'}),patch('urllib.request.urlopen',return_value=Reply()) as request:
            generate('ده نص جديد.',Path(td)/'a.wav');generate('ده نص جديد.',Path(td)/'b.wav')
            self.assertEqual(request.call_count,1)
            self.assertEqual((Path(td)/'a.wav').read_bytes(),(Path(td)/'b.wav').read_bytes())
    def test_daily_quota_error_is_not_retried_or_replaced(self):
        exc=HTTPError('https://provider.invalid',429,'rate limit',{},io.BytesIO(b'{"quota":"requests_per_day"}'))
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'GEMINI_API_KEY':'test-placeholder','GEMINI_TTS_API_KEY':'','VOICE_CACHE_DIR':td+'/cache','API_BUDGET_PATH':td+'/budget.sqlite3'}),patch('urllib.request.urlopen',side_effect=exc) as request:
            with self.assertRaisesRegex(RuntimeError,'HTTP 429'):generate('ده نص.',Path(td)/'a.wav')
            self.assertEqual(request.call_count,1);self.assertFalse((Path(td)/'a.wav').exists())
    def test_budget_survives_repeated_callers(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'API_BUDGET_PATH':td+'/budget.sqlite3','GEMINI_TTS_RUN_BUDGET':'1','GEMINI_TTS_MIN_INTERVAL':'0'}):
            reserve('tts','test-model','test-placeholder')
            with self.assertRaises(BudgetExceeded):reserve('tts','test-model','test-placeholder')
if __name__=='__main__':unittest.main()
