import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from production_v2.durable import GitLedgerStore, DurabilityError
from production_v2.ledger import Conflict


class DurableGitLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / 'remote.git'
        self.repo = self.root / 'first'
        self.git(None, 'init', '--bare', str(self.remote))
        self.git(None, 'init', '-b', 'main', str(self.repo))
        self.git(self.repo, 'config', 'user.name', 'fixture')
        self.git(self.repo, 'config', 'user.email', 'fixture@example.test')
        (self.repo / 'state').mkdir()
        (self.repo / 'state/professional_topics.json').write_text(json.dumps({'episodes':[{'topic_key':'old-subject','receipts':{'youtube':{'id':'retained-post'}}}]}))
        (self.repo / 'source.txt').write_text('application source\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-m', 'initial source')
        self.git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.repo, 'push', '-u', 'origin', 'main')
        self.git(None, '--git-dir='+str(self.remote), 'symbolic-ref', 'HEAD', 'refs/heads/main')

    @staticmethod
    def git(repo, *args):
        prefix = ['git'] + (['-C',str(repo)] if repo else [])
        return subprocess.check_output(prefix + list(args), stderr=subprocess.DEVNULL).decode().strip()

    def clone(self, name):
        repo=self.root/name
        self.git(None, 'clone', str(self.remote), str(repo))
        return repo

    def reserve(self, ledger, slot='candidate-one'):
        ledger.reserve(slot, slot+'-subject','2026-12-01T15:00:00Z',{'topic_key':slot+'-subject'})

    def test_bootstrap_checkpoint_restores_reservation_without_touching_source_or_index(self):
        (self.repo/'source.txt').write_text('staged user work\n')
        self.git(self.repo,'add','source.txt')
        before_head=self.git(self.repo,'rev-parse','HEAD')
        before_index=self.git(self.repo,'write-tree')
        before_branch=self.git(self.repo,'branch','--show-current')
        store=GitLedgerStore(self.repo)
        with store.restore(self.root/'local.sqlite3') as ledger:
            self.reserve(ledger)
            store(ledger)
            self.assertEqual(ledger.db.execute('SELECT COUNT(*) FROM legacy_files').fetchone()[0],1)
        self.assertEqual(self.git(self.repo,'rev-parse','HEAD'),before_head)
        self.assertEqual(self.git(self.repo,'write-tree'),before_index)
        self.assertEqual(self.git(self.repo,'branch','--show-current'),before_branch)
        self.assertEqual((self.repo/'source.txt').read_text(),'staged user work\n')
        other=self.clone('restored')
        with GitLedgerStore(other).restore(self.root/'restored.sqlite3') as ledger:
            self.assertEqual(ledger.db.execute('SELECT slot FROM reservations').fetchone()[0],'candidate-one')
            raw=ledger.db.execute('SELECT content FROM legacy_files').fetchone()[0]
            self.assertIn(b'retained-post',raw)

    def test_competing_writer_is_rejected_without_reset_or_force(self):
        first=GitLedgerStore(self.repo)
        first_ledger=first.restore(self.root/'first.sqlite3')
        self.addCleanup(first_ledger.close)
        second=GitLedgerStore(self.clone('second'))
        second_ledger=second.restore(self.root/'second.sqlite3')
        self.addCleanup(second_ledger.close)
        self.reserve(first_ledger,'winner')
        first(first_ledger)
        second_parent=second.parent
        self.reserve(second_ledger,'loser-retained-locally')
        with self.assertRaises(DurabilityError):second(second_ledger)
        self.assertEqual(second.parent,second_parent)
        self.assertEqual(second_ledger.db.execute('SELECT slot FROM reservations').fetchone()[0],'loser-retained-locally')
        with GitLedgerStore(self.clone('reader')).restore(self.root/'reader.sqlite3') as ledger:
            self.assertEqual(ledger.db.execute('SELECT slot FROM reservations').fetchone()[0],'winner')

    def test_divergent_local_ledger_is_never_overwritten(self):
        store=GitLedgerStore(self.repo)
        path=self.root/'local.sqlite3'
        with store.restore(path) as ledger:self.reserve(ledger)
        before=path.read_bytes()
        with self.assertRaises(Conflict):GitLedgerStore(self.repo).restore(path)
        self.assertEqual(path.read_bytes(),before)

    def test_auth_failure_is_not_mistaken_for_empty_remote(self):
        store=GitLedgerStore(self.repo)
        result=subprocess.CompletedProcess([],128,b'',b'access denied')
        with patch.object(store,'_git',return_value=result):
            with self.assertRaises(DurabilityError):store.restore(self.root/'never-created.sqlite3')
        self.assertFalse((self.root/'never-created.sqlite3').exists())

    def test_missing_remote_does_not_reset_retained_local_file(self):
        path=self.root/'retained.sqlite3';path.write_bytes(b'important retained state')
        with self.assertRaises(Conflict):GitLedgerStore(self.repo).restore(path)
        self.assertEqual(path.read_bytes(),b'important retained state')

    def test_corrupt_remote_database_is_not_restored(self):
        self.git(self.repo,'checkout','-b',GitLedgerStore.BRANCH)
        target=self.repo/GitLedgerStore.LEDGER_FILE
        target.write_bytes(b'not a SQLite ledger')
        self.git(self.repo,'add',str(target.relative_to(self.repo)))
        self.git(self.repo,'commit','-m','corrupt fixture')
        self.git(self.repo,'push','origin',GitLedgerStore.BRANCH)
        path=self.root/'never-created.sqlite3'
        with self.assertRaises(DurabilityError):GitLedgerStore(self.repo).restore(path)
        self.assertFalse(path.exists())

if __name__=='__main__':unittest.main()
