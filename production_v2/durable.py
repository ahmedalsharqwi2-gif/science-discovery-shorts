"""Persist candidate ledgers on an isolated Git branch before remote mutations.

The checkout's source branch, working files and real index remain untouched.
Normal fast-forward pushes provide optimistic concurrency; a competing writer
blocks this job rather than resetting, merging SQLite bytes, or force pushing.
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile

from .ledger import Ledger, Conflict


class DurabilityError(RuntimeError):
    """Git access, state integrity or a competing writer prevents persistence."""


class GitLedgerStore:
    BRANCH = 'codex/production-v2-state'
    LEDGER_FILE = 'state/production-v2-ledger.sqlite3'

    def __init__(self, repository):
        self.repository = Path(repository).resolve()
        self.parent = None
        self.initialized = False

    def _git(self, *args, env=None, check=True, input=None):
        return subprocess.run(['git', '-C', str(self.repository), *args],
                              env=env, input=input, capture_output=True, check=check)

    @staticmethod
    def _validate_database(path):
        try:
            with sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True) as connection:
                if connection.execute('PRAGMA quick_check').fetchone() != ('ok',):
                    raise DurabilityError('Persisted candidate ledger failed SQLite integrity checks')
                tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {'legacy_files', 'reservations', 'intents', 'receipts', 'events'} <= tables:
                    raise DurabilityError('Persisted database is not a production v2 ledger')
        except sqlite3.DatabaseError as error:
            raise DurabilityError('Persisted candidate ledger is not a valid SQLite database') from error

    def restore(self, path):
        """Return an open Ledger; never overwrite divergent retained local state."""
        if self.initialized:
            raise DurabilityError('Create a new store object to perform another restore')
        path = Path(path).resolve()
        if path == self.repository or path.is_dir():
            raise ValueError('A separate candidate ledger file is required')
        ref = 'refs/heads/' + self.BRANCH
        found = self._git('ls-remote', '--exit-code', 'origin', ref, check=False)
        if found.returncode not in (0, 2):
            raise DurabilityError('Could not inspect candidate state branch; authentication/network access must be restored')
        if found.returncode == 2:
            # Only Git's explicit no-match status permits first-time bootstrap.
            if path.exists():
                raise Conflict('Remote state is absent but local state exists; reconcile without resetting local history')
            ledger = Ledger(path)
            try:
                ledger.import_legacy(self.repository)
                self.initialized = True
                self.checkpoint(ledger)
            except BaseException:
                ledger.close()
                raise
            return ledger
        # Pin the SHA actually fetched. A race between discovery and fetch is
        # safe: fetch's latest tree is the state used as this writer's parent.
        try:
            self._git('fetch', '--no-tags', 'origin', ref)
            self.parent = self._git('rev-parse', '--verify', 'FETCH_HEAD^{commit}').stdout.decode().strip()
            raw = self._git('show', self.parent + ':' + self.LEDGER_FILE).stdout
        except subprocess.CalledProcessError as error:
            raise DurabilityError('Could not fetch the retained candidate ledger; no empty replacement was created') from error
        with tempfile.TemporaryDirectory(prefix='v2-ledger-restore-') as folder:
            snapshot = Path(folder) / 'retained.sqlite3'
            snapshot.write_bytes(raw)
            self._validate_database(snapshot)
            if path.exists():
                if not path.is_file() or path.read_bytes() != raw:
                    raise Conflict('Local candidate ledger diverges from durable state; preserve and reconcile it')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation prevents concurrent restores overwriting a
                # reservation another local process created in the meantime.
                with path.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
        self.initialized = True
        return Ledger(path)

    def checkpoint(self, ledger):
        """Atomically snapshot SQLite and push it normally; failure blocks callers."""
        if not self.initialized:
            raise DurabilityError('Restore/bootstrap durable state before checkpointing')
        if ledger.db.in_transaction:
            raise DurabilityError('Commit the ledger transaction before durable persistence')
        with tempfile.TemporaryDirectory(prefix='v2-ledger-checkpoint-') as folder:
            folder = Path(folder)
            snapshot = folder / 'ledger.sqlite3'
            with sqlite3.connect(snapshot) as destination:
                ledger.db.backup(destination)
            self._validate_database(snapshot)
            env = dict(os.environ, GIT_INDEX_FILE=str(folder / 'index'))
            try:
                parent = self.parent or self._git('rev-parse', '--verify', 'HEAD^{commit}').stdout.decode().strip()
                self._git('read-tree', parent, env=env)
                blob = self._git('hash-object', '-w', str(snapshot)).stdout.decode().strip()
                self._git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + self.LEDGER_FILE, env=env)
                tree = self._git('write-tree', env=env).stdout.decode().strip()
                commit = self._git('-c', 'user.name=production-v2-state',
                    '-c', 'user.email=production-v2-state@users.noreply.github.com',
                    'commit-tree', tree, '-p', parent,
                    input=b'Persist append-only candidate ledger before further work [skip ci]\n').stdout.decode().strip()
                self._git('push', 'origin', commit + ':refs/heads/' + self.BRANCH)
            except subprocess.CalledProcessError as error:
                raise DurabilityError('Candidate ledger persistence failed; a competing update or access failure requires reconciliation, never force push') from error
        self.parent = commit
        return commit

    __call__ = checkpoint
