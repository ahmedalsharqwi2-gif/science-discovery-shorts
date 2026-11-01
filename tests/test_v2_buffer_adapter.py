from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from production_v2.buffer_adapter import BufferAdapter, PROFILES

NOW=datetime(2026,12,1,10,tzinfo=timezone.utc)
DUE='2026-12-01T15:00:00Z'
MAP={'youtube':'a','facebook':'b','instagram':'c'}
MEDIA='https://example.test/new-film.mp4'

class BufferAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'config').mkdir()
        self.write('professional_destinations.json',{'profile':'news','existing_bindings_confirmed_by_user':True,'buffer_channel_ids':MAP})
        self.write('production_v2.json',{'profile':'news','active_pipeline':'legacy'})
        self.client=Mock();self.client._create_buffer_post.return_value={'id':'accepted-id','dueAt':DUE}
        self.query=Mock(side_effect=self.response)
        self.env=patch.dict('os.environ',{'GITHUB_REPOSITORY':'ahmedalsharqwi2-gif/ai-news-daily','BUFFER_API_KEY':'test-only-key'})
        self.env.start();self.addCleanup(self.env.stop)
        self.adapter=BufferAdapter('news',self.root,title='A current title',caption='A current caption',client=self.client,query=self.query,clock=lambda:NOW)
        self.paused=False
    def write(self,name,data):
        (self.root/'config'/name).write_text(json.dumps(data))
    def activate_fixture(self):
        self.write('production_v2_acceptance.json',{'cutover_eligible':True,'profiles':{profile:{'passed':True} for profile in PROFILES}})
        digest=hashlib.sha256((self.root/'config/production_v2_acceptance.json').read_bytes()).hexdigest()
        self.write('production_v2.json',{'profile':'news','active_pipeline':'production_v2','acceptance_report_sha256':digest})
    def response(self,text):
        if 'organizations' in text:return {'account':{'organizations':[{'id':'org'}]}}
        if 'channels(' in text:return {'channels':[{'id':identifier,'service':service,'isQueuePaused':self.paused,'displayName':'Renamed approved channel'} for service,identifier in MAP.items()]}
        if 'post(' in text:return {'post':{'id':'accepted-id','channelId':'a','status':'scheduled','dueAt':DUE,'assets':[{'source':MEDIA}]}}
        raise AssertionError(text)
    def test_inactive_cutover_blocks_without_provider_calls(self):
        with self.assertRaises(PermissionError):self.adapter.preflight(MAP)
        with self.assertRaises(PermissionError):self.adapter.submit(channel_id='a',due_at=DUE,media_url=MEDIA)
        self.query.assert_not_called();self.client._create_buffer_post.assert_not_called()
    def test_changed_acceptance_hash_blocks(self):
        self.activate_fixture()
        with (self.root/'config/production_v2_acceptance.json').open('a') as stream:stream.write(' ')
        with self.assertRaises(PermissionError):self.adapter.preflight(MAP)
        self.query.assert_not_called()
    def test_repository_scope_does_not_reuse_another_repository_key(self):
        self.activate_fixture()
        with patch.dict('os.environ',{'GITHUB_REPOSITORY':'ahmedalsharqwi2-gif/science-discovery-shorts'}):
            with self.assertRaises(PermissionError):self.adapter.preflight(MAP)
        self.query.assert_not_called()
    def test_confirmed_ids_survive_display_name_changes(self):
        self.activate_fixture()
        self.assertEqual(self.adapter.preflight(dict(MAP)),MAP)
        self.assertEqual(self.client.schedule_mode,'customScheduled')
        self.client.schedule_mode='addToQueue'
        self.adapter.submit(channel_id='a',due_at=DUE,media_url=MEDIA)
        self.assertEqual(self.client.schedule_mode,'customScheduled')
        args=self.client._create_buffer_post.call_args.kwargs
        self.assertEqual(args['service'],'youtube');self.assertEqual(args['due_at'],DUE)
        self.assertEqual(args['media_url'],MEDIA)
    def test_changed_binding_or_paused_channel_fails_preflight(self):
        self.activate_fixture()
        with self.assertRaises(ValueError):self.adapter.preflight({**MAP,'youtube':'other'})
        self.query.assert_not_called()
        self.paused=True
        with self.assertRaises(PermissionError):self.adapter.preflight(MAP)
        self.client._create_buffer_post.assert_not_called()
    def test_expired_connection_fails_before_submission(self):
        self.activate_fixture();self.query.side_effect=RuntimeError('Provider authorization failed')
        with self.assertRaises(ConnectionError):self.adapter.preflight(MAP)
        self.client._create_buffer_post.assert_not_called()
    def test_late_or_nonabsolute_due_never_posts_immediately(self):
        self.activate_fixture();self.adapter.preflight(MAP)
        for due in ('2026-12-01T09:00:00Z','2026-12-02T15:00:00Z','2026-12-01T15:00:00'):
            with self.assertRaises(ValueError):self.adapter.submit(channel_id='a',due_at=due,media_url=MEDIA)
        self.client._create_buffer_post.assert_not_called()
    def test_lookup_preserves_exact_provider_media_and_identity(self):
        self.assertEqual(self.adapter.lookup('accepted-id'),{'id':'accepted-id','channel_id':'a','status':'scheduled','due_at':DUE,'media_url':MEDIA})
        self.query.return_value={};self.query.side_effect=lambda text:{'post':{'id':'accepted-id','dueAt':DUE,'assets':[{'source':MEDIA},{'source':'https://example.test/other'}]}}
        with self.assertRaises(ValueError):self.adapter.lookup('accepted-id')
    def test_full_five_profile_acceptance_is_required(self):
        self.activate_fixture()
        report={'cutover_eligible':True,'profiles':{profile:{'passed':True} for profile in PROFILES if profile!='stickman'}}
        self.write('production_v2_acceptance.json',report)
        digest=hashlib.sha256((self.root/'config/production_v2_acceptance.json').read_bytes()).hexdigest()
        self.write('production_v2.json',{'profile':'news','active_pipeline':'production_v2','acceptance_report_sha256':digest})
        with self.assertRaises(PermissionError):self.adapter.preflight(MAP)
        self.query.assert_not_called()

if __name__=='__main__':unittest.main()
