import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from production_v2.export_review import export_review, StatusStore, STATUS_BRANCH

class ReviewExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.run=self.root/'candidate'
        self.store=Mock();self.store.save.return_value='d'*40
        self.env=patch.dict(os.environ,{'GITHUB_REPOSITORY':'ahmedalsharqwi2-gif/ai-news-daily',
            'GITHUB_RUN_ID':'123','GITHUB_RUN_ATTEMPT':'2','GITHUB_SHA':'a'*40,'GITHUB_TOKEN':'test-only-token'})
        self.env.start();self.addCleanup(self.env.stop)
        self.factory=Mock()
        self.factory.return_value._release_asset_url.return_value='https://github.com/example/review/download/actual.mp4'
    def evidence(self):
        out=self.run/'output';out.mkdir(parents=True)
        film=out/'candidate-review.mp4';film.write_bytes(b'mocked-already-decoded-film')
        report={'validated':True,'decode':'PASS','width':1080,'height':1920,'duration':125,
                'sha256':hashlib.sha256(film.read_bytes()).hexdigest(),'fresh_topic_verified':False,'generation_origin':'archive'}
        (out/'candidate-verification.json').write_text(json.dumps(report))
        (self.run/'generation-verification.json').write_text(json.dumps({'fresh_topic_verified':False}))
        delivery=self.run/'professional_motion/delivery';delivery.mkdir(parents=True)
        (delivery/'narration.source.json').write_text(json.dumps({'provider':'Gemini TTS','voice':'Charon',
            'interaction_id':'provider-evidence','output_sha256':'c'*64,'secret_field':'never-export-this'}))
        return film
    def call(self,stage):
        return export_review('news',self.run,stage,root=self.root,uploader_factory=self.factory,store=self.store)
    def test_started_needs_no_film_or_http_and_retains_run_identity(self):
        result=self.call('started')
        self.factory.assert_not_called();self.store.save.assert_called_once()
        self.assertEqual(result['run_id'],'123');self.assertFalse(result['complete_film_verified'])
        self.assertIsNone(result['media_url']);self.assertTrue(result['status_persisted'])
    def test_missing_or_failed_film_never_uploads_or_claims_completion(self):
        for stage in ['failure','cancelled','success']:
            result=self.call(stage)
            self.assertFalse(result['complete_film_verified']);self.assertIsNone(result['media_url'])
            self.assertEqual(result['evidence_error_class'],'ValueError')
            self.assertNotEqual(result['stage'],'success')
        self.factory.assert_not_called()
    def test_changed_bytes_rejected_before_upload(self):
        film=self.evidence();film.write_bytes(b'changed-after-verification')
        result=self.call('success')
        self.assertEqual(result['stage'],'failure');self.assertFalse(result['complete_film_verified'])
        self.factory.assert_not_called()
    def test_success_uses_actual_url_and_restores_media_identity(self):
        film=self.evidence();seen=[]
        self.factory.side_effect=lambda:(seen.append(os.environ['PRODUCTION_MEDIA_ID']) or self.factory.return_value)
        with patch.dict(os.environ,{'PRODUCTION_MEDIA_ID':'original'}):
            result=self.call('success');self.assertEqual(os.environ['PRODUCTION_MEDIA_ID'],'original')
        self.assertEqual(seen,['v2-review-news-123-2'])
        self.factory.return_value._release_asset_url.assert_called_once_with(film)
        self.assertEqual(result['media_url'],'https://github.com/example/review/download/actual.mp4')
        self.assertFalse(result['fresh_topic_verified']);self.assertFalse(result['cutover_eligible'])
        self.assertNotIn('secret_field',result['narration_provenance'])
    def test_api_failure_is_sanitized_and_failure_status_still_persists(self):
        self.evidence();self.factory.return_value._release_asset_url.side_effect=RuntimeError('SECRET must not be echoed')
        result=self.call('success')
        self.assertEqual(result['stage'],'failure');self.assertEqual(result['evidence_error_class'],'RuntimeError')
        self.assertIsNone(result['media_url']);self.assertNotIn('SECRET',json.dumps(result))
        self.assertTrue(result['status_persisted'])
    def test_failure_does_not_upload_even_if_completed_media_exists(self):
        self.evidence();result=self.call('failure')
        self.assertTrue(result['complete_film_verified']);self.assertEqual(result['stage'],'failure')
        self.factory.assert_not_called();self.assertIsNone(result['media_url'])
    def test_readonly_audit_exports_without_film_and_omits_unknown_fields(self):
        audit=self.root/'audit.json'
        audit.write_text(json.dumps({'profile':'news','read_only':True,'live_access_available':True,
            'secret':'do-not-retain','episodes':[{'slot':'daily-example','live_verified':False,
            'posts':{'youtube':{'observed_post_id':'p','status':'failed','credential':'not-exported'}}}]}))
        result=export_review('news',self.run,'success',root=self.root,store=self.store,
            uploader_factory=self.factory,audit_report=audit,status_branch='codex/production-v2-audit-status')
        self.assertEqual(result['stage'],'success');self.assertEqual(result['kind'],'buffer_audit')
        self.assertFalse(result['complete_film_verified']);self.assertIsNone(result['media_url'])
        self.assertEqual(result['buffer_audit']['episodes'][0]['posts']['youtube']['status'],'failed')
        self.assertNotIn('do-not-retain',json.dumps(result));self.assertNotIn('not-exported',json.dumps(result))
        self.factory.assert_not_called()
    def test_status_export_cannot_target_main(self):
        with self.assertRaises(ValueError):
            export_review('news',self.run,'started',root=self.root,store=self.store,status_branch='main')
        self.store.save.assert_not_called()

    def test_wrong_repository_context_rejected_before_any_external_action(self):
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'someone/other'}):
            with self.assertRaises(PermissionError):self.call('started')
        self.store.save.assert_not_called();self.factory.assert_not_called()

class StatusGitTests(unittest.TestCase):
    def test_status_history_preserves_source_branch_and_real_index(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);remote=folder/'remote.git';repo=folder/'repo'
            def run(*args,cwd=None):return subprocess.check_output(args,cwd=cwd,stderr=subprocess.PIPE).decode().strip()
            run('git','init','--bare',str(remote));run('git','init','-b','main',str(repo))
            run('git','config','user.name','test',cwd=repo);run('git','config','user.email','test@example.invalid',cwd=repo)
            (repo/'source.txt').write_text('retained source')
            run('git','add','source.txt',cwd=repo);run('git','commit','-m','initial',cwd=repo)
            run('git','remote','add','origin',str(remote),cwd=repo)
            (repo/'staged.txt').write_text('staged work');run('git','add','staged.txt',cwd=repo)
            before_head=run('git','rev-parse','HEAD',cwd=repo);before_index=(repo/'.git/index').read_bytes()
            store=StatusStore(repo)
            first=store.save('123','2',{'stage':'started','complete_film_verified':False})
            second=store.save('123','2',{'stage':'failure','complete_film_verified':False})
            self.assertNotEqual(first,second)
            self.assertEqual(run('git','rev-parse','HEAD',cwd=repo),before_head)
            self.assertEqual(run('git','branch','--show-current',cwd=repo),'main')
            self.assertEqual((repo/'.git/index').read_bytes(),before_index)
            self.assertEqual(run('git','--git-dir',str(remote),'show',second+':source.txt'),'retained source')
            prefix='reviews/production-v2-runs/123-2/'
            latest=json.loads(run('git','--git-dir',str(remote),'show',second+':'+prefix+'status.json'))
            started=json.loads(run('git','--git-dir',str(remote),'show',second+':'+prefix+'started.json'))
            self.assertEqual(latest['stage'],'failure');self.assertEqual(started['stage'],'started')
            self.assertEqual(run('git','--git-dir',str(remote),'rev-parse','refs/heads/'+STATUS_BRANCH),second)

class StatusRaceTests(unittest.TestCase):
    def test_competing_status_writer_rejects_without_force_push(self):
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder);remote=folder/'remote.git';repo=folder/'repo'
            def run(*args,cwd=None):return subprocess.check_output(args,cwd=cwd,stderr=subprocess.PIPE).decode().strip()
            run('git','init','--bare',str(remote));run('git','init','-b','main',str(repo))
            run('git','config','user.name','test',cwd=repo);run('git','config','user.email','test@example.invalid',cwd=repo)
            (repo/'source.txt').write_text('retained source');run('git','add','source.txt',cwd=repo)
            run('git','commit','-m','initial',cwd=repo);run('git','remote','add','origin',str(remote),cwd=repo)
            rival=StatusStore(repo)
            class RacingStore(StatusStore):
                raced=False
                def git(self,*args,**kwargs):
                    if args[0]=='push' and not self.raced:
                        self.raced=True
                        rival.save('124','1',{'stage':'started'})
                    return super().git(*args,**kwargs)
            with self.assertRaises(subprocess.CalledProcessError):
                RacingStore(repo).save('123','1',{'stage':'started'})
            tip=run('git','--git-dir',str(remote),'rev-parse','refs/heads/'+STATUS_BRANCH)
            names=run('git','--git-dir',str(remote),'ls-tree','-r','--name-only',tip)
            self.assertIn('124-1/status.json',names);self.assertNotIn('123-1/status.json',names)
            self.assertEqual(run('git','branch','--show-current',cwd=repo),'main')

if __name__=='__main__':unittest.main()
