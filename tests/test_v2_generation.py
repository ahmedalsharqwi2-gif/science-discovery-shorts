"""Mock remote generation and ASR; exercise real isolation, ledger and bundle checks."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch
import wave

from production_v2.generate import generate
from production_v2.ledger import Conflict, Ledger


class CandidateGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        (self.repo / 'state').mkdir(parents=True)
        (self.repo / 'config').mkdir()
        (self.repo / 'professional_motion').mkdir()
        self.legacy = b'{"version":2,"episodes":[{"topic_key":"old-topic","video_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","receipts":{"youtube":{"id":"keep-this-post"}}}]}'
        (self.repo / 'state/professional_topics.json').write_bytes(self.legacy)
        (self.repo / 'config/accepted_voice.json').write_text('{"speaker":"Charon"}')
        (self.repo / 'professional_motion/catalog.json').write_text('{"news":[]}')
        self.run = self.repo / '.work/candidate'
        self.ledger = self.root / 'candidate.sqlite3'
        self.calls = []
        self.story = {'profile': 'news', 'topic_key': 'fresh-topic',
            'canonical_subject': 'Distinct verified subject',
            'source': {'url': 'https://openai.com/new-subject'},
            'scenes': [{'id': str(i), 'narration': 'mock speech'} for i in range(8)]}
        self.editorial = types.ModuleType('professional_motion.editorial')
        self.editorial.ROOT = self.repo / 'professional_motion'
        self.editorial.STATE = Path('state/professional_topics.json')
        self.original_root, self.original_state = self.editorial.ROOT, self.editorial.STATE
        self.editorial.prepare = self.prepare
        self.voice = types.ModuleType('professional_motion.voice_job')
        self.voice.main = self.narrate
        self.credentials = types.ModuleType('professional_motion.credentials')
        self.credentials.preflight = lambda: self.calls.append('credentials')
        self.modules = {'professional_motion.editorial': self.editorial,
            'professional_motion.voice_job': self.voice,
            'professional_motion.credentials': self.credentials}
        self.cwd = Path.cwd()

    def prepare(self, profile, slot):
        self.calls.append('prepare')
        self.assertEqual(Path.cwd(), self.run)
        self.assertEqual(self.editorial.ROOT, self.run / 'professional_motion')
        self.assertEqual(os.environ['API_BUDGET_PATH'], str(self.repo / 'state/api_budget.sqlite3'))
        self.assertEqual(os.environ['VOICE_CACHE_DIR'], str(self.repo / '.voice_cache'))
        self.assertEqual(os.environ['FACTORY_DAILY'], 'false')
        delivery = self.editorial.ROOT / 'delivery'
        delivery.mkdir()
        (delivery / 'story.json').write_text(json.dumps(self.story))
        # Existing implementation reserves in its local copied registry.
        state = json.loads(self.editorial.STATE.read_text())
        state['episodes'].append({'slot': slot, 'story': self.story})
        self.editorial.STATE.write_text(json.dumps(state))
        return deepcopy(self.story)

    def narrate(self):
        self.calls.append('voice')
        delivery = self.run / 'professional_motion/delivery'
        with Ledger(self.ledger) as ledger:
            self.assertEqual(ledger.db.execute('SELECT count(*) FROM reservations').fetchone()[0], 1)
        with wave.open(str(delivery / 'narration.wav'), 'wb') as audio:
            audio.setparams((1, 2, 100, 0, 'NONE', 'not compressed'))
            audio.writeframes(b'\0\0' * 12000)
        timing = {'duration': 120, 'coverage': 1, 'topic_key': self.story['topic_key'],
            'scenes': [{'id': str(i), 'start': i*15, 'end': (i+1)*15} for i in range(8)],
            'story_sha256': hashlib.sha256((delivery / 'story.json').read_bytes()).hexdigest(),
            'audio_sha256': hashlib.sha256((delivery / 'narration.wav').read_bytes()).hexdigest()}
        (delivery / 'timing.json').write_text(json.dumps(timing))

    def run_candidate(self, **kwargs):
        with patch.dict('sys.modules', self.modules):
            return generate('news', self.run, self.ledger, repository=self.repo, **kwargs)

    def assert_restored(self):
        self.assertEqual(Path.cwd(), self.cwd)
        self.assertEqual(self.editorial.ROOT, self.original_root)
        self.assertEqual(self.editorial.STATE, self.original_state)
        self.assertEqual((self.repo / 'state/professional_topics.json').read_bytes(), self.legacy)

    def test_full_generation_preserves_original_records_and_restores_process(self):
        with patch.dict(os.environ, {}, clear=True):
            result = self.run_candidate()
            self.assertNotIn('API_BUDGET_PATH', os.environ)
            self.assertNotIn('VOICE_CACHE_DIR', os.environ)
            self.assertNotIn('FACTORY_DAILY', os.environ)
        self.assert_restored()
        self.assertEqual(self.calls, ['credentials', 'prepare', 'voice'])
        self.assertTrue(result['fresh_topic_verified'])
        self.assertFalse(result['publishable'])
        self.assertEqual(result['duration'], 120)
        with Ledger(self.ledger) as ledger:
            raw = ledger.db.execute("SELECT content FROM legacy_files WHERE path='state/professional_topics.json'").fetchone()[0]
            self.assertEqual(raw, self.legacy)
            self.assertEqual(ledger.db.execute('SELECT count(*) FROM reservations').fetchone()[0], 1)
            self.assertEqual(ledger.db.execute("SELECT count(*) FROM events WHERE kind='candidate_story'").fetchone()[0], 1)

    def test_failed_checkpoint_prevents_any_voice_request(self):
        def blocked(ledger):
            self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0],1)
            raise RuntimeError('Git state push rejected')
        with self.assertRaisesRegex(RuntimeError,'push rejected'):
            self.run_candidate(persist=blocked)
        self.assertEqual(self.calls,['credentials','prepare'])
        self.assert_restored()

    def test_missing_credentials_has_no_partial_writes(self):
        def missing():
            raise RuntimeError('Missing repository Actions secret')
        self.credentials.preflight = missing
        with self.assertRaisesRegex(RuntimeError, 'Missing'):
            self.run_candidate()
        self.assertFalse(self.run.exists())
        self.assertFalse(self.ledger.exists())
        self.assert_restored()

    def test_provider_failure_restores_globals_and_retains_reservation(self):
        def failure():
            self.calls.append('voice')
            raise RuntimeError('Provider unavailable')
        self.voice.main = failure
        with patch.dict(os.environ, {'FACTORY_DAILY': 'true'}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'Provider unavailable'):
                self.run_candidate()
            self.assertEqual(os.environ['FACTORY_DAILY'], 'true')
            self.assertNotIn('API_BUDGET_PATH', os.environ)
        self.assert_restored()
        self.assertTrue((self.run / 'professional_motion/delivery/story.json').exists())
        with Ledger(self.ledger) as ledger:
            self.assertEqual(ledger.db.execute('SELECT count(*) FROM reservations').fetchone()[0], 1)
            payload = json.loads(ledger.db.execute("SELECT payload FROM events WHERE kind='candidate_generation_failed'").fetchone()[0])
            self.assertTrue(payload['reservation_retained'])

    def test_duplicate_topic_is_blocked_before_narration(self):
        with Ledger(self.ledger) as ledger:
            ledger.reserve('previous-candidate', self.story['topic_key'], '2026-10-31T15:00:00Z', self.story)
        with self.assertRaises(Conflict):
            self.run_candidate()
        self.assertNotIn('voice', self.calls)
        self.assert_restored()

    def test_failed_prepare_restores_process_and_does_not_call_voice(self):
        def failure(*args):
            raise ValueError('No source-backed new subject')
        self.editorial.prepare = failure
        with self.assertRaisesRegex(ValueError, 'No source-backed'):
            self.run_candidate()
        self.assertNotIn('voice', self.calls)
        self.assert_restored()

    def test_short_or_unmeasured_voice_cannot_be_claimed_generated(self):
        def invalid_voice():
            self.narrate()
            timing_file = self.run / 'professional_motion/delivery/timing.json'
            timing = json.loads(timing_file.read_text())
            timing['coverage'] = .2
            timing_file.write_text(json.dumps(timing))
        self.voice.main = invalid_voice
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.run_candidate()
        self.assertFalse((self.run / 'generation-verification.json').exists())
        self.assert_restored()

    def test_existing_candidate_directory_is_never_overwritten(self):
        self.run.mkdir(parents=True)
        artifact = self.run / 'keep.mp4'
        artifact.write_bytes(b'untouched')
        with self.assertRaises(FileExistsError):
            self.run_candidate()
        self.assertEqual(artifact.read_bytes(), b'untouched')
        self.assertNotIn('prepare', self.calls)
        self.assertFalse(self.ledger.exists())

    def test_ephemeral_candidate_ledger_is_rejected(self):
        with patch.dict('sys.modules', self.modules):
            with self.assertRaisesRegex(ValueError, 'durable candidate'):
                generate('news', self.run, self.run / 'ledger.sqlite3', repository=self.repo)
        self.assertFalse(self.run.exists())

    def test_existing_legacy_topic_is_blocked_before_narration(self):
        self.story['topic_key'] = 'old-topic'
        with self.assertRaises(Conflict):
            self.run_candidate()
        self.assertNotIn('voice', self.calls)
        self.assert_restored()

    def test_candidate_ledger_cannot_mutate_original_budget_database(self):
        with patch.dict('sys.modules', self.modules):
            with self.assertRaisesRegex(ValueError, 'API budget'):
                generate('news', self.run, self.repo / 'state/api_budget.sqlite3', repository=self.repo)
        self.assertFalse(self.run.exists())
        self.assertFalse((self.repo / 'state/api_budget.sqlite3').exists())
