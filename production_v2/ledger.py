"""Append-only local production ledger. A pending submission is never auto-retried.

Persist the database together with all historical state before external mutations.
SQLite provides process locking on one machine; distributed jobs still need the
repository-wide Actions concurrency group and durable database persistence.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlsplit, urlunsplit


class Conflict(RuntimeError):
    pass


class ReconciliationRequired(Conflict):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def normalized_due(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('A timezone-aware durable due time is required')
    return result.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def tokens(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ('topic_key', 'canonical_subject') and isinstance(item, str) and item:
                yield 'topic', item.casefold().strip()
            if key in ('video_sha256', 'publication_video_sha256', 'sha256') and isinstance(item, str) and len(item) == 64:
                yield 'video', item.lower()
            if key in ('url', 'source_url', 'canonical_url') and isinstance(item, str):
                parts = urlsplit(item)
                if parts.scheme == 'https' and parts.hostname:
                    yield 'source', urlunsplit(('https', parts.netloc.lower(), parts.path.rstrip('/'), '', ''))
            if key in ('due_at', 'scheduled_at', 'dueAt') and isinstance(item, str):
                try:
                    yield 'due', normalized_due(item)
                except ValueError:
                    pass
            if key == 'slot' and isinstance(item, str):
                yield 'slot', item
            yield from tokens(item)
    elif isinstance(value, list):
        for item in value:
            yield from tokens(item)


class Ledger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS legacy_files(path TEXT, sha256 TEXT, content BLOB NOT NULL,
            PRIMARY KEY(path,sha256));
        CREATE TABLE IF NOT EXISTS legacy_tokens(kind TEXT, token TEXT, PRIMARY KEY(kind,token));
        CREATE TABLE IF NOT EXISTS reservations(slot TEXT PRIMARY KEY, topic TEXT UNIQUE NOT NULL,
            due TEXT NOT NULL, story_sha256 TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS reservation_tokens(kind TEXT, token TEXT,
            slot TEXT NOT NULL REFERENCES reservations(slot), PRIMARY KEY(kind,token));
        CREATE TABLE IF NOT EXISTS videos(slot TEXT PRIMARY KEY REFERENCES reservations(slot),
            sha256 TEXT UNIQUE NOT NULL, evidence TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS intents(slot TEXT REFERENCES videos(slot), service TEXT,
            channel TEXT NOT NULL, due TEXT NOT NULL, media_url TEXT NOT NULL,
            PRIMARY KEY(slot,service));
        CREATE TABLE IF NOT EXISTS schedule_claims(channel TEXT, due TEXT, slot TEXT NOT NULL,
            PRIMARY KEY(channel,due));
        CREATE TABLE IF NOT EXISTS submission_acks(slot TEXT, service TEXT, post_id TEXT UNIQUE NOT NULL,
            PRIMARY KEY(slot,service), FOREIGN KEY(slot,service) REFERENCES intents(slot,service));
        CREATE TABLE IF NOT EXISTS receipts(slot TEXT, service TEXT, post_id TEXT UNIQUE NOT NULL,
            payload TEXT NOT NULL, PRIMARY KEY(slot,service),
            FOREIGN KEY(slot,service) REFERENCES intents(slot,service));
        CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            at TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL);
        ''')
        for table in ('legacy_files', 'legacy_tokens', 'reservations', 'reservation_tokens', 'videos', 'intents', 'schedule_claims', 'submission_acks', 'receipts', 'events'):
            self.db.executescript(f'''
            CREATE TRIGGER IF NOT EXISTS immutable_{table}_update BEFORE UPDATE ON {table}
                BEGIN SELECT RAISE(ABORT,'append-only ledger'); END;
            CREATE TRIGGER IF NOT EXISTS immutable_{table}_delete BEFORE DELETE ON {table}
                BEGIN SELECT RAISE(ABORT,'append-only ledger'); END;
            ''')

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def event(self, kind, payload):
        self.db.execute('INSERT INTO events(at,kind,payload) VALUES(?,?,?)',
                        (datetime.now(timezone.utc).isoformat(), kind, encode(payload)))

    def import_legacy(self, root):
        """Preserve exact source bytes and dedup tokens, never rewrite source files."""
        root = Path(root).resolve()
        paths = sorted(set(p for p in (root / 'state').rglob('*.json') if p.is_file()) |
                       {root / name for name in ('topic_history.json', 'film_topics.json',
                         'professional_topics.json', 'publication_receipts.json') if (root / name).is_file()})
        records = []
        with self.transaction():
            for path in paths:
                raw = path.read_bytes()
                # Invalid JSON blocks migration rather than quietly losing history.
                parsed = json.loads(raw)
                digest = hashlib.sha256(raw).hexdigest()
                relative = path.relative_to(root).as_posix()
                self.db.execute('INSERT OR IGNORE INTO legacy_files VALUES(?,?,?)', (relative, digest, raw))
                self.db.executemany('INSERT OR IGNORE INTO legacy_tokens VALUES(?,?)', set(tokens(parsed)))
                records.append({'path': relative, 'sha256': digest, 'bytes': len(raw)})
            self.event('legacy_snapshot', records)
        return records

    def reserve(self, slot, topic, due, story):
        topic = topic.casefold().strip()
        if not slot or not topic:
            raise ValueError('Slot and canonical topic identity required')
        story_hash = hashlib.sha256(encode(story).encode()).hexdigest()
        with self.transaction():
            identity_tokens = {('topic', topic), ('slot', slot)} | set(tokens(story))
            if slot.startswith('daily-'):
                identity_tokens.add(('due', normalized_due(due)))
            identity_tokens = {(kind, token) for kind, token in identity_tokens if kind in ('topic', 'slot', 'source', 'due') and (kind != 'due' or slot.startswith('daily-'))}
            for kind, token in identity_tokens:
                if self.db.execute('SELECT 1 FROM legacy_tokens WHERE kind=? AND token=?', (kind, token)).fetchone():
                    raise Conflict('Already present in legacy history: ' + kind)
            try:
                self.db.execute('INSERT INTO reservations VALUES(?,?,?,?)', (slot, topic, due, story_hash))
                self.db.executemany('INSERT INTO reservation_tokens VALUES(?,?,?)', [(kind, token, slot) for kind, token in identity_tokens])
            except sqlite3.IntegrityError as error:
                raise Conflict('Slot, topic, canonical subject, or source already reserved; resume exact reservation') from error
            self.event('reserved', {'slot': slot, 'topic': topic, 'due': due, 'story_sha256': story_hash})
        return story_hash

    def register_video(self, slot, evidence):
        digest = evidence['sha256']
        if evidence.get('decode') != 'PASS' or evidence.get('validated') is not True:
            raise ValueError('Full validated media evidence required')
        with self.transaction():
            if self.db.execute('SELECT 1 FROM legacy_tokens WHERE kind=? AND token=?', ('video', digest)).fetchone():
                raise Conflict('Previously produced video hash')
            try:
                self.db.execute('INSERT INTO videos VALUES(?,?,?)', (slot, digest, encode(evidence)))
            except sqlite3.IntegrityError as error:
                raise Conflict('Video, slot, or reservation conflict') from error
            self.event('video_validated', {'slot': slot, **evidence})

    def receipt(self, slot, service):
        row = self.db.execute('SELECT payload FROM receipts WHERE slot=? AND service=?', (slot, service)).fetchone()
        return json.loads(row[0]) if row else None

    def begin_submission(self, slot, service, channel, due, media_url):
        with self.transaction():
            if self.db.execute('SELECT 1 FROM intents WHERE slot=? AND service=?', (slot, service)).fetchone():
                raise ReconciliationRequired('Existing submission intent: query provider before any retry')
            reservation = self.db.execute('SELECT due FROM reservations WHERE slot=?', (slot,)).fetchone()
            if not reservation or normalized_due(reservation[0]) != normalized_due(due):
                raise Conflict('Due time differs from durable reservation')
            if self.db.execute('SELECT 1 FROM legacy_tokens WHERE kind=? AND token=?', ('due', normalized_due(due))).fetchone():
                raise Conflict('Legacy publication already occupies this due time; reconcile retained posts before cutover')
            try:
                self.db.execute('INSERT INTO schedule_claims VALUES(?,?,?)', (channel, normalized_due(due), slot))
            except sqlite3.IntegrityError as error:
                raise Conflict('Another slot already claimed this channel and due time') from error
            self.db.execute('INSERT INTO intents VALUES(?,?,?,?,?)', (slot, service, channel, due, media_url))
            self.event('submission_intent', {'slot': slot, 'service': service, 'channel': channel,
                                             'due': due, 'media_url': media_url})

    def submission(self, slot, service):
        row = self.db.execute('SELECT channel,due,media_url FROM intents WHERE slot=? AND service=?', (slot, service)).fetchone()
        return dict(zip(('channel_id','due_at','media_url'), row)) if row else None

    def acknowledged(self, slot, service):
        row = self.db.execute('SELECT post_id FROM submission_acks WHERE slot=? AND service=?', (slot, service)).fetchone()
        return row[0] if row else None

    def acknowledge(self, slot, service, post_id):
        """Retain an accepted ID before lookup; this is not a verified receipt."""
        if not isinstance(post_id, str) or not post_id:
            raise ValueError('A real accepted post ID is required')
        with self.transaction():
            current = self.acknowledged(slot, service)
            if current:
                if current != post_id:
                    raise Conflict('Do not replace an accepted post ID')
                return current
            self.db.execute('INSERT INTO submission_acks VALUES(?,?,?)', (slot, service, post_id))
            self.event('submission_acknowledged', {'slot': slot, 'service': service, 'post_id': post_id})
        return post_id

    def reconcile(self, slot, service, observed):
        """Record independently queried provider evidence, including media identity."""
        with self.transaction():
            intent = self.db.execute('SELECT channel,due,media_url FROM intents WHERE slot=? AND service=?', (slot, service)).fetchone()
            if not intent:
                raise Conflict('No durable submission intent')
            channel, due, media_url = intent
            expected = datetime.fromisoformat(due.replace('Z', '+00:00'))
            actual = datetime.fromisoformat(observed.get('due_at', '').replace('Z', '+00:00'))
            if not observed.get('id') or observed.get('channel_id') != channel or observed.get('media_url') != media_url or observed.get('status') != 'scheduled' or actual != expected:
                raise ReconciliationRequired('Provider has not confirmed exact scheduled post/media/due/channel')
            acknowledged = self.acknowledged(slot, service)
            if acknowledged and acknowledged != observed.get('id'):
                raise Conflict('Provider receipt differs from retained accepted post ID')
            current = self.receipt(slot, service)
            if current:
                if current.get('id') != observed.get('id'):
                    raise Conflict('Receipt already preserved; do not replace post ID')
                self.event('provider_receipt_reverified', {'slot': slot, 'service': service, **observed})
                return current
            self.db.execute('INSERT INTO receipts VALUES(?,?,?,?)', (slot, service, observed['id'], encode(observed)))
            self.event('provider_receipt', {'slot': slot, 'service': service, **observed})
            return observed
