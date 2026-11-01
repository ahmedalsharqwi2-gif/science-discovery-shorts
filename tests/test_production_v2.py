from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from production_v2.ledger import Ledger, Conflict, ReconciliationRequired
from production_v2.media import verify
from production_v2.publisher import schedule_three
from production_v2.schedule import window, require_duration, require_future_due

DUE = '2026-12-01T15:00:00Z'
NOW = datetime(2026, 12, 1, 10, tzinfo=timezone.utc)
MEDIA = 'https://example.test/unique.mp4'
MAP = {'youtube': 'a', 'facebook': 'b', 'instagram': 'c'}


class ScheduleTests(unittest.TestCase):
    def test_cairo_summer_and_winter_same_day(self):
        for month, hour, due_hour in [(7, 6, 14), (12, 7, 15)]:
            now = datetime(2026, month, 1, hour, tzinfo=timezone.utc)
            result = window(now)
            self.assertEqual(result['reason'], 'eligible')
            self.assertEqual(datetime.fromisoformat(result['due_at'].replace('Z', '+00:00')).hour, due_hour)
            self.assertEqual(result['slot'], f'daily-2026-{month:02d}-01')
            self.assertEqual(window(now.replace(hour=hour-1))['reason'], 'too_early')
            # Late Actions dispatch within the window remains valid.
            self.assertTrue(window(now.replace(hour=hour+4))['run'])
            closed = window(now.replace(hour=hour+6))
            self.assertEqual(closed['reason'], 'missed')
            self.assertEqual(closed['due_at'][:10], result['due_at'][:10])

    def test_late_slot_never_posts_immediately_or_rolls(self):
        for due in ('2026-12-01T10:00:00Z', '2026-12-02T15:00:00Z'):
            with self.assertRaises(ValueError):
                require_future_due(due, NOW)
        self.assertEqual(require_future_due(DUE, NOW).hour, 15)

    def test_duration_contract(self):
        for value in (0, 119.99, 180, 181, float('nan'), float('inf')):
            with self.assertRaises(ValueError):
                require_duration(value)
        self.assertEqual(require_duration(120), 120)
        self.assertEqual(require_duration(179.99), 179.99)

    def test_naive_clock_rejected(self):
        with self.assertRaises(ValueError):
            window(datetime(2026, 1, 1))


class FakeProvider:
    def __init__(self):
        self.created = []
        self.posts = {}
        self.fail_channel = None
        self.expired = False

    def preflight(self, mapping):
        if self.expired:
            raise PermissionError('expired connection')

    def submit(self, **kwargs):
        if kwargs['channel_id'] == self.fail_channel:
            raise TimeoutError('Remote acceptance unknown')
        identifier = 'post-' + kwargs['channel_id']
        self.created.append(identifier)
        self.posts[identifier] = {'id': identifier, 'channel_id': kwargs['channel_id'],
                                  'due_at': kwargs['due_at'], 'media_url': kwargs['media_url'],
                                  'status': 'scheduled'}
        return {'id': identifier}

    def lookup(self, identifier):
        return self.posts[identifier]


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.ledger = Ledger(self.root / 'ledger.sqlite3')

    def tearDown(self):
        self.ledger.close()
        self.folder.cleanup()

    def ready(self):
        self.ledger.reserve('daily-2026-12-01', 'new-subject', DUE, {'topic_key': 'new-subject'})
        self.ledger.register_video('daily-2026-12-01', {'sha256': 'a'*64, 'decode': 'PASS', 'validated': True})

    def test_legacy_exact_bytes_receipts_and_hash_preserved(self):
        state = self.root / 'state'
        state.mkdir()
        raw = b'{ "episodes": [{"slot":"daily-old","story":{"topic_key":"old-topic"}, "video_sha256":"' + b'b'*64 + b'","receipts":{"youtube":{"id":"real-post"}}}]}\n'
        source = state / 'professional_topics.json'
        source.write_bytes(raw)
        records = self.ledger.import_legacy(self.root)
        self.assertEqual(source.read_bytes(), raw)
        saved = self.ledger.db.execute('SELECT content FROM legacy_files').fetchone()[0]
        self.assertEqual(saved, raw)
        self.assertEqual(records[0]['sha256'], hashlib.sha256(raw).hexdigest())
        for slot, topic in [('daily-old', 'new'), ('new', 'old-topic')]:
            with self.assertRaises(Conflict):
                self.ledger.reserve(slot, topic, DUE, {})
        self.ledger.reserve('new', 'unique', DUE, {})
        with self.assertRaises(Conflict):
            self.ledger.register_video('new', {'sha256': 'b'*64, 'decode': 'PASS', 'validated': True})

    def test_malformed_legacy_json_aborts_without_partial_import(self):
        (self.root / 'state').mkdir()
        (self.root / 'state/a.json').write_text('{}')
        (self.root / 'state/z.json').write_text('{bad')
        with self.assertRaises(json.JSONDecodeError):
            self.ledger.import_legacy(self.root)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM legacy_files').fetchone()[0], 0)

    def test_append_only_tables_reject_destructive_edits(self):
        self.ready()
        for query in ('DELETE FROM reservations', "UPDATE videos SET sha256='different'"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.ledger.db.execute(query)

    def test_legacy_next_day_schedule_blocks_new_daily_slot_for_same_due(self):
        (self.root/'state').mkdir()
        (self.root/'state/old.json').write_text(json.dumps({'slot':'daily-2026-11-30','due_at':DUE,'status':'scheduled'}))
        self.ledger.import_legacy(self.root)
        with self.assertRaises(Conflict):
            self.ledger.reserve('daily-2026-12-01','new-topic',DUE,{})
        self.ledger.reserve('candidate-review','new-topic',DUE,{})
        self.ledger.register_video('candidate-review',{'sha256':'c'*64,'validated':True,'decode':'PASS'})
        with self.assertRaises(Conflict):
            self.ledger.begin_submission('candidate-review','youtube','a',DUE,MEDIA)

    def test_distinct_candidate_slots_cannot_submit_same_channel_due_twice(self):
        self.ready()
        self.ledger.begin_submission('daily-2026-12-01','youtube','a',DUE,MEDIA)
        self.ledger.reserve('candidate-two','other-topic',DUE,{})
        self.ledger.register_video('candidate-two',{'sha256':'c'*64,'validated':True,'decode':'PASS'})
        with self.assertRaises(Conflict):
            self.ledger.begin_submission('candidate-two','youtube','a','2026-12-01T15:00:00+00:00',MEDIA)

    def test_alias_title_cannot_reuse_canonical_subject_or_source(self):
        self.ledger.reserve('first', 'original-key', DUE, {'canonical_subject':'Same physical subject','source':{'url':'https://science.example/topic?utm_source=first'}})
        for story in [{'canonical_subject':'same physical subject'}, {'source':{'url':'https://science.example/topic#chapter'}}]:
            with self.assertRaises(Conflict):
                self.ledger.reserve('second', 'invented-new-title', DUE, story)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM reservations').fetchone()[0], 1)

    def test_same_day_duplicate_topic_and_video_blocked(self):
        self.ready()
        with self.assertRaises(Conflict):
            self.ledger.reserve('daily-2026-12-01', 'other-topic', DUE, {})
        with self.assertRaises(Conflict):
            self.ledger.reserve('daily-2026-12-02', 'new-subject', DUE, {})
        self.ledger.reserve('other', 'other', DUE, {})
        with self.assertRaises(Conflict):
            self.ledger.register_video('other', {'sha256': 'a'*64, 'decode': 'PASS', 'validated': True})

    def test_parallel_jobs_cannot_reserve_same_slot(self):
        path = self.root / 'ledger.sqlite3'
        def reserve(topic):
            with Ledger(path) as ledger:
                try:
                    ledger.reserve('same-slot', topic, DUE, {})
                    return 'reserved'
                except Conflict:
                    return 'blocked'
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(reserve, ['topic-one', 'topic-two']))
        self.assertCountEqual(results, ['reserved', 'blocked'])

    def test_partial_submission_retry_never_duplicates_accepted_destination(self):
        self.ready()
        provider = FakeProvider()
        provider.fail_channel = 'b'
        with self.assertRaises(TimeoutError):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(provider.created, ['post-a'])
        provider.fail_channel = None
        with self.assertRaises(ReconciliationRequired):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(provider.created, ['post-a'])
        # Provider reconciliation is independent and explicit after ambiguous acceptance.
        provider.posts['post-b'] = {'id': 'post-b', 'channel_id': 'b', 'due_at': DUE,
                                    'media_url': MEDIA, 'status': 'scheduled'}
        self.ledger.reconcile('daily-2026-12-01', 'facebook', provider.lookup('post-b'))
        result = schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(set(result), set(MAP))
        self.assertEqual(provider.created, ['post-a', 'post-c'])

    def test_known_accepted_id_survives_lookup_failure_without_resubmission(self):
        self.ready()
        provider = FakeProvider()
        with patch.object(provider, 'lookup', side_effect=ConnectionError('post lookup unavailable')):
            with self.assertRaises(ConnectionError):
                schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(self.ledger.acknowledged('daily-2026-12-01','youtube'), 'post-a')
        self.assertIsNone(self.ledger.receipt('daily-2026-12-01','youtube'))
        result=schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(set(result),set(MAP))
        self.assertEqual(provider.created,['post-a','post-b','post-c'])

    def test_retry_cannot_change_channel_or_media_binding(self):
        self.ready()
        provider = FakeProvider()
        schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        for mapping, media in [({**MAP, 'youtube': 'changed'}, MEDIA),
                                (MAP, 'https://example.test/replaced.mp4')]:
            with self.assertRaises(Conflict):
                schedule_three(self.ledger, 'daily-2026-12-01', mapping, DUE, media, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(len(provider.created), 3)

    def test_retry_queries_provider_and_rejects_stale_scheduled_receipt(self):
        self.ready()
        provider = FakeProvider()
        schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        provider.posts['post-a']['status'] = 'failed'
        with self.assertRaises(ReconciliationRequired):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(len(provider.created), 3)

    def test_durable_persistence_failure_blocks_external_submission(self):
        self.ready()
        provider=FakeProvider()
        with self.assertRaisesRegex(RuntimeError, 'persistence callback'):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW)
        def failed_persistence(ledger):
            self.assertIsNotNone(ledger.submission('daily-2026-12-01','youtube'))
            raise OSError('Durable storage unavailable')
        with self.assertRaises(OSError):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=failed_persistence)
        self.assertEqual(provider.created,[])

    def test_expired_connection_creates_no_submission_intent(self):
        self.ready()
        provider = FakeProvider()
        provider.expired = True
        with self.assertRaises(PermissionError):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(self.ledger.db.execute('SELECT COUNT(*) FROM intents').fetchone()[0], 0)

    def test_missing_or_failed_video_blocks_mutations(self):
        self.ledger.reserve('daily-2026-12-01', 'subject', DUE, {})
        with self.assertRaises(ValueError):
            self.ledger.register_video('daily-2026-12-01', {'sha256': 'a'*64, 'decode': 'FAIL'})
        provider = FakeProvider()
        with self.assertRaises(sqlite3.IntegrityError):
            schedule_three(self.ledger, 'daily-2026-12-01', MAP, DUE, MEDIA, provider, now=NOW, persist=lambda ledger: None)
        self.assertEqual(provider.created, [])

    def test_wrong_media_or_expired_provider_receipt_is_not_accepted(self):
        self.ready()
        self.ledger.begin_submission('daily-2026-12-01', 'youtube', 'a', DUE, MEDIA)
        evidence = {'id': 'x', 'channel_id': 'a', 'due_at': DUE,
                    'media_url': MEDIA, 'status': 'failed'}
        with self.assertRaises(ReconciliationRequired):
            self.ledger.reconcile('daily-2026-12-01', 'youtube', evidence)
        evidence.update(status='scheduled', media_url='https://example.test/old.mp4')
        with self.assertRaises(ReconciliationRequired):
            self.ledger.reconcile('daily-2026-12-01', 'youtube', evidence)


class MediaTests(unittest.TestCase):
    def test_missing_file_rejected_before_probe(self):
        with patch('production_v2.media.subprocess.run') as run:
            with self.assertRaises(ValueError):
                verify('/does/not/exist.mp4')
            run.assert_not_called()

    def test_short_visuals_with_long_audio_fail_before_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'film.mp4'
            path.write_bytes(b'fake-container-for-mocked-probe')
            for duration, frames in [('1', '30'), ('130', '30')]:
                probe = type('Result', (), {'stdout': json.dumps({'format': {'duration': '130'}, 'streams': [
                    {'codec_type': 'video', 'width': 1080, 'height': 1920, 'duration': duration,
                     'avg_frame_rate': '30/1', 'nb_read_frames': frames},
                    {'codec_type': 'audio', 'duration': '130'}]})})()
                with patch('production_v2.media.subprocess.run', return_value=probe) as run:
                    with self.assertRaises(ValueError):
                        verify(path)
                    self.assertEqual(run.call_count, 1)

    def test_decoder_failure_cannot_be_reported_as_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'film.mp4'
            path.write_bytes(b'fake-container-for-mocked-decoder')
            probe = type('Result', (), {'stdout': json.dumps({'format': {'duration': '130'}, 'streams': [
                {'codec_type': 'video', 'width': 1080, 'height': 1920, 'duration': '130', 'avg_frame_rate': '30/1', 'nb_read_frames': '3900'}, {'codec_type': 'audio', 'duration': '130'}]})})()
            decode = type('Result', (), {'returncode': 1, 'stderr': 'corrupt packet'})()
            with patch('production_v2.media.subprocess.run', side_effect=[probe, decode]):
                with self.assertRaisesRegex(ValueError, 'decode failed'):
                    verify(path)


class ActivationGateTests(unittest.TestCase):
    def test_missing_fifth_blocks_cutover_even_if_other_profiles_pass(self):
        from production_v2.gate import evaluate
        supplied = {profile: {} for profile in ('science', 'horror', 'history', 'news')}
        with patch('production_v2.gate.check_profile', side_effect=lambda p, e: {'passed': True}):
            report = evaluate({'profiles': supplied})
        self.assertFalse(report['cutover_eligible'])
        self.assertEqual(report['active_pipeline'], 'legacy')
        self.assertFalse(report['profiles']['stickman']['passed'])

    def test_archived_full_film_cannot_satisfy_new_pipeline_gate(self):
        from production_v2.gate import evaluate, PROFILES
        evidence = {'profiles': {p: {'origin': 'archive_validation'} for p in PROFILES}}
        report = evaluate(evidence)
        self.assertFalse(report['cutover_eligible'])
        self.assertTrue(all('Archived' in r['reason'] for r in report['profiles'].values()))

    def test_legacy_mutation_invalidates_acceptance_before_media_validation(self):
        from production_v2.gate import check_profile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'state').mkdir()
            state = root / 'state/topics.json'
            state.write_text('{"topics":[]}')
            old_hash = hashlib.sha256(state.read_bytes()).hexdigest()
            state.write_text('{"topics":["changed"]}')
            with self.assertRaisesRegex(ValueError, 'Legacy state changed'):
                check_profile('science', {'origin': 'new_generation', 'repo_root': str(root),
                    'legacy_snapshot': [{'path': 'state/topics.json', 'sha256': old_hash}]})


if __name__ == '__main__':
    unittest.main()
