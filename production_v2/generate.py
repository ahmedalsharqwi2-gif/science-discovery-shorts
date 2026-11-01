"""Generate an isolated fresh review candidate using the repository's approved providers.

Run as a single process from the repository root. The durable candidate ledger,
original API budget and original voice cache must survive between Actions runs.
This module never schedules posts, changes legacy state, or activates a workflow.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import uuid

from .ledger import Ledger
from .review import bundle
from .schedule import window


def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


@contextmanager
def isolated_editor(editorial, run_dir, repository):
    """Restore cwd, provider budgets/cache environment and mutable editor globals on error."""
    previous_cwd, previous_root, previous_state = Path.cwd(), editorial.ROOT, editorial.STATE
    names = ('API_BUDGET_PATH', 'VOICE_CACHE_DIR', 'FACTORY_DAILY')
    previous_env = {name: os.environ.get(name) for name in names}
    def original_path(name, default):
        value = Path(previous_env[name] or default)
        return str(value.resolve() if value.is_absolute() else (repository / value).resolve())
    try:
        os.environ['API_BUDGET_PATH'] = original_path('API_BUDGET_PATH', 'state/api_budget.sqlite3')
        os.environ['VOICE_CACHE_DIR'] = original_path('VOICE_CACHE_DIR', '.voice_cache')
        # This is review generation, not the legacy duration-revision daily path.
        os.environ['FACTORY_DAILY'] = 'false'
        editorial.ROOT = run_dir / 'professional_motion'
        editorial.STATE = run_dir / 'state/professional_topics.json'
        os.chdir(run_dir)
        yield
    finally:
        editorial.ROOT, editorial.STATE = previous_root, previous_state
        os.chdir(previous_cwd)
        for name, value in previous_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _copy_inputs(repository, run_dir):
    """Copy exact public resource/state bytes, excluding secrets and cache databases."""
    copied = []
    candidates = list((repository / 'state').rglob('*.json'))
    candidates.extend(repository / name for name in (
        'topic_history.json', 'film_topics.json', 'professional_topics.json',
        'publication_receipts.json', 'professional_motion/catalog.json',
        'config/accepted_voice.json', 'config/professional_models.json'))
    for source in sorted(set(candidates)):
        if not source.is_file():
            continue
        # A symlinked resource escaping the repository must not silently copy secrets.
        if not source.resolve().is_relative_to(repository):
            raise ValueError('Input resource resolves outside the repository')
        relative = source.relative_to(repository)
        target = run_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append({'path': relative.as_posix(), 'sha256': _digest(source)})
    return copied


def _merge_candidate_history(ledger, run_dir):
    """Candidate reservations join the isolated editor's dedup view, never legacy JSON."""
    state = run_dir / 'state/professional_topics.json'
    data = json.loads(state.read_text()) if state.exists() else {'version': 2, 'episodes': []}
    for (payload,) in ledger.db.execute("SELECT payload FROM events WHERE kind='candidate_story'"):
        row = json.loads(payload)
        story = row['story']
        data['episodes'].append({'slot': row['slot'], 'topic_key': story['topic_key'],
            'canonical_subject': story.get('canonical_subject', story['topic_key']),
            'url': story.get('source', {}).get('url', ''), 'status': 'candidate_reserved',
            'story': story})
    _write(state, data)


def generate(profile, run_dir, ledger_path, *, repository=None, then_review=False, persist=None):
    if profile not in ('science', 'horror', 'history', 'news'):
        raise ValueError('Unknown channel profile')
    repository = Path(repository or Path.cwd()).resolve()
    run_dir, ledger_path = Path(run_dir).resolve(), Path(ledger_path).resolve()
    credentials = importlib.import_module('professional_motion.credentials')
    # Before mkdir, ledger construction, snapshots, HTTP requests or source writes.
    credentials.preflight()
    if run_dir == repository or repository.is_relative_to(run_dir):
        raise ValueError('A separate fresh candidate run directory is required')
    if any(run_dir.is_relative_to(repository / name) for name in ('state', 'config', 'professional_motion')):
        raise ValueError('Candidate directory must not overlap production resources')
    budget_path = Path(os.environ.get('API_BUDGET_PATH', 'state/api_budget.sqlite3'))
    budget_path = budget_path.resolve() if budget_path.is_absolute() else (repository / budget_path).resolve()
    if ledger_path == budget_path:
        raise ValueError('Candidate ledger must not reuse the original API budget database')
    if any(ledger_path.is_relative_to(repository / name) for name in ('state', 'config', 'professional_motion')):
        raise ValueError('Candidate ledger must not modify production state or API budget databases')
    if ledger_path.is_relative_to(run_dir) or ledger_path.suffix != '.sqlite3':
        raise ValueError('Use a durable candidate .sqlite3 ledger outside the run directory')
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError('Existing candidate files are retained; choose a fresh run directory')
    editorial = importlib.import_module('professional_motion.editorial')
    voice_job = importlib.import_module('professional_motion.voice_job')
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / 'professional_motion').mkdir(exist_ok=True)
    slot = 'candidate-' + profile + '-' + uuid.uuid4().hex
    due = window(datetime.now(timezone.utc))['due_at']
    with Ledger(ledger_path) as ledger:
        ledger.import_legacy(repository)
        inputs = _copy_inputs(repository, run_dir)
        _merge_candidate_history(ledger, run_dir)
        _write(run_dir / 'source-snapshot.json', {'repository': str(repository), 'inputs': inputs})
        reserved = False
        try:
            with isolated_editor(editorial, run_dir, repository):
                story = editorial.prepare(profile, slot)
                story_file = run_dir / 'professional_motion/delivery/story.json'
                if not story.get('topic_key') or story.get('profile') != profile:
                    raise ValueError('Prepared story identity does not match the channel')
                if json.loads(story_file.read_text()) != story:
                    raise ValueError('Prepared story and retained delivery bytes differ')
                # Transactional conflict check MUST happen before TTS or ASR.
                ledger.reserve(slot, story['topic_key'], due, story)
                reserved = True
                with ledger.transaction():
                    ledger.event('candidate_story', {'slot': slot, 'profile': profile,
                        'story': story, 'story_bytes_sha256': _digest(story_file),
                        'run_dir': str(run_dir), 'review_only': True})
                if persist is not None:
                    persist(ledger)
                voice_job.main()
                checked_story, timing = bundle(run_dir / 'professional_motion/delivery', profile)
                result = {'slot': slot, 'profile': profile, 'topic_key': checked_story['topic_key'],
                    'duration': timing['duration'], 'story_sha256': _digest(story_file),
                    'audio_sha256': _digest(run_dir / 'professional_motion/delivery/narration.wav'),
                    'generated_in_isolation': True, 'review_only': True, 'publishable': False,
                    'fresh_topic_verified': True, 'legacy_state_unchanged': True,
                    'ledger': str(ledger_path),
                    'ledger_persistence_requirement': 'Persist the shared ledger, legacy state and API budget between all runs before enabling any active workflow.'}
            # Verify all protected inputs still match the exact source snapshot.
            if any(_digest(repository / row['path']) != row['sha256'] for row in inputs):
                raise ValueError('Production inputs changed during candidate generation')
            _write(run_dir / 'generation-verification.json', result)
            with ledger.transaction():
                ledger.event('candidate_generated', result)
            if persist is not None:
                persist(ledger)
        except BaseException as error:
            measured_seconds = None
            wav_path = run_dir / 'professional_motion/delivery/narration.wav'
            if wav_path.is_file():
                import wave
                try:
                    with wave.open(str(wav_path)) as wav:
                        measured_seconds = wav.getnframes() / wav.getframerate()
                except (wave.Error, EOFError):
                    pass
            _write(run_dir / 'generation-failure.json', {'slot': slot, 'profile': profile,
                'error_class': type(error).__name__, 'reservation_retained': reserved,
                'legacy_film_not_used_as_fallback': True, 'publishable': False,
                'failed_phase': 'narration_or_alignment' if reserved else 'story_or_reservation',
                'measured_narration_seconds': measured_seconds,
                'timing_present': (run_dir / 'professional_motion/delivery/timing.json').is_file()})
            with ledger.transaction():
                ledger.event('candidate_generation_failed', {'slot': slot,
                    'error_class': type(error).__name__, 'reservation_retained': reserved,
                    'run_dir': str(run_dir)})
            if persist is not None:
                persist(ledger)
            raise
    if then_review:
        from .review import main as review_main
        import sys
        old_argv = sys.argv
        try:
            sys.argv = ['production_v2.review', '--profile', profile,
                '--delivery-dir', str(run_dir / 'professional_motion/delivery'),
                '--output-dir', str(run_dir / 'output')]
            review_main()
        finally:
            sys.argv = old_argv
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['science', 'horror', 'history', 'news'], required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--then-review', action='store_true')
    parser.add_argument('--git-state', action='store_true', help='Restore and checkpoint the candidate ledger on its separate Git state branch')
    args = parser.parse_args()
    persist = None
    if args.git_state:
        importlib.import_module('professional_motion.credentials').preflight()
        from .durable import GitLedgerStore
        store = GitLedgerStore(Path.cwd())
        with store.restore(args.ledger):
            pass
        persist = store.checkpoint
    print(json.dumps(generate(args.profile, args.run_dir, args.ledger,
                             then_review=args.then_review, persist=persist), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
