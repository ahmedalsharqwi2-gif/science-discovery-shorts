import importlib.util,json,tempfile,unittest,os
from pathlib import Path
from datetime import datetime,timezone
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
runner=module('runner');host=module('publish_static')
class RuntimeTests(unittest.TestCase):
    def test_cairo_dst_window(self):
        config={}
        self.assertTrue(runner.daily_window(config,datetime(2026,7,1,6,tzinfo=timezone.utc)))
        self.assertFalse(runner.daily_window(config,datetime(2026,7,1,10,tzinfo=timezone.utc)))
        self.assertTrue(runner.daily_window(config,datetime(2026,12,1,7,tzinfo=timezone.utc)))
    def test_secrets_permission_and_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'secret';p.write_text('{"GEMINI_API_KEY":"dummy"}');p.chmod(0o644)
            with self.assertRaises(ValueError):runner.secrets(p)
            p.chmod(0o600);self.assertEqual(runner.secrets(p)['GEMINI_API_KEY'],'dummy')
            p.write_text('{"PATH":"bad"}')
            with self.assertRaises(ValueError):runner.secrets(p)
    def test_media_url_rejects_credentials_local_and_http(self):
        for value in ['http://example.com','https://user:pass@example.com','https://localhost','https://127.0.0.1','https://10.0.0.1','https://example.com?key=foo']:
            with self.subTest(value=value),self.assertRaises(ValueError):host.media_url(value,'a.mp4')
        self.assertEqual(host.media_url('https://media.example.com','science/a.mp4'),'https://media.example.com/science/a.mp4')
    def test_immutable_media_and_readable_dir(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);video=p/'v.mp4';video.write_bytes(b'video')
            name,target=host.store_media(video,p/'public','science','review-1')
            self.assertEqual(host.store_media(video,p/'public','science','review-1'),(name,target))
            self.assertEqual(target.stat().st_mode&0o777,0o644)
            self.assertEqual(target.parent.stat().st_mode&0o777,0o755)
            target.write_bytes(b'changed')
            with self.assertRaises(ValueError):host.store_media(video,p/'public','science','review-1')
    def test_approval_does_not_load_credentials(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'secrets',side_effect=AssertionError('must not read')):
            result=runner.execute({'profile':'science','path':d},{'runtime_root':d},'daily',{'run':False},'x')
            self.assertEqual(result['status'],'approval_pending')
    def test_uncertain_publication_never_retries_command(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=root/'key.json';key.write_text('{"GEMINI_API_KEY":"dummy"}');key.chmod(0o600)
            runner.save(root/'journals/science.json',{'slot':'daily-test','stage':'publish','status':'failed','completed':['finish']})
            with patch.object(runner,'command',side_effect=AssertionError('must not retry')):
                result=runner.execute({'profile':'science','path':d,'secrets_file':str(key),'repository':'owner/repo'},{'runtime_root':d},'daily',{'run':True,'slot':'daily-test','due':'x'},'x',True)
            self.assertEqual(result['error_class'],'PublicationReconciliationRequired')
    def test_completed_daily_does_not_rerun(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);key=root/'key.json';key.write_text('{"GEMINI_API_KEY":"dummy"}');key.chmod(0o600)
            runner.save(root/'journals/science.json',{'slot':'daily-test','stage':'done','status':'complete','completed':['publish']})
            with patch.object(runner,'command',side_effect=AssertionError('must not rerun')):
                result=runner.execute({'profile':'science','path':d,'secrets_file':str(key),'repository':'owner/repo'},{'runtime_root':d},'daily',{'run':True,'slot':'daily-test'},'x',True)
            self.assertEqual(result['status'],'already_complete')
if __name__=='__main__':unittest.main()
