"""Export CI review status and validated review media; never create social posts.

The started/failure paths use only Python's standard library and native Git.
Release uploads are loaded lazily after a successful, fingerprinted film exists.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile

REPOSITORIES = {
    'science': 'science-discovery-shorts', 'horror': 'arabic-horror-stories',
    'history': 'documented-history-stories', 'news': 'ai-news-daily',
    'stickman': 'stickman-what-if-shorts',
}
STATUS_BRANCH = 'codex/production-v2-status'
STATUS_BRANCHES = {STATUS_BRANCH, 'codex/production-v2-audit-status'}
AUDIT_KEYS = {'checked_at', 'profile', 'read_only', 'live_access_available', 'episodes', 'slot',
    'video_sha256', 'retained_status', 'due_at', 'live_verified', 'posts', 'no_posts_created',
    'problem', 'retained_post_id', 'expected_channel_id', 'live_checked', 'observed_post_id',
    'channel_id', 'status', 'scheduled_at', 'sent_at', 'external_link', 'media_urls',
    'post_and_channel_match', 'due_matches', 'media_matches', 'verified', 'error_class'}


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            checksum.update(chunk)
    return checksum.hexdigest()


@contextmanager
def media_identity(value):
    previous = os.environ.get('PRODUCTION_MEDIA_ID')
    os.environ['PRODUCTION_MEDIA_ID'] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('PRODUCTION_MEDIA_ID', None)
        else:
            os.environ['PRODUCTION_MEDIA_ID'] = previous


class StatusStore:
    def __init__(self, root, branch=STATUS_BRANCH):
        if branch not in STATUS_BRANCHES:
            raise ValueError('Only isolated review/audit status branches may be written')
        self.branch = branch
        self.root = Path(root).resolve()

    def git(self, *args, env=None, check=True, input=None):
        return subprocess.run(['git', '-C', str(self.root), *args], env=env,
                              capture_output=True, check=check, input=input)

    def save(self, run, attempt, status):
        ref = 'refs/heads/' + self.branch
        found = self.git('ls-remote', '--exit-code', 'origin', ref, check=False)
        if found.returncode not in (0, 2):
            raise RuntimeError('Status branch access is unavailable')
        if found.returncode == 0:
            self.git('fetch', '--no-tags', 'origin', ref)
            parent = self.git('rev-parse', '--verify', 'FETCH_HEAD^{commit}').stdout.decode().strip()
        else:
            parent = self.git('rev-parse', '--verify', 'HEAD^{commit}').stdout.decode().strip()
        with tempfile.TemporaryDirectory(prefix='v2-review-export-') as folder:
            folder = Path(folder)
            env = dict(os.environ, GIT_INDEX_FILE=str(folder / 'index'))
            self.git('read-tree', parent, env=env)
            body = (json.dumps(status, ensure_ascii=False, indent=2) + '\n').encode()
            blob = self.git('hash-object', '-w', '--stdin', input=body).stdout.decode().strip()
            prefix = f'reviews/production-v2-runs/{run}-{attempt}/'
            for name in ('status.json', status['stage'] + '.json'):
                self.git('update-index', '--add', '--cacheinfo',
                         '100644,' + blob + ',' + prefix + name, env=env)
            tree = self.git('write-tree', env=env).stdout.decode().strip()
            commit = self.git('-c', 'user.name=production-v2-review',
                '-c', 'user.email=production-v2-review@users.noreply.github.com',
                'commit-tree', tree, '-p', parent,
                input=b'Retain production v2 review status [skip ci]\n').stdout.decode().strip()
            # A competing update rejects this push. Never reset or force push.
            self.git('push', 'origin', commit + ':' + ref)
        return commit


def context(profile):
    if profile not in REPOSITORIES:
        raise ValueError('Unknown repository review profile')
    expected = 'ahmedalsharqwi2-gif/' + REPOSITORIES[profile]
    if os.getenv('GITHUB_REPOSITORY') != expected:
        raise PermissionError('Review export must use the matching repository Actions context')
    run, attempt, source = (os.getenv(name, '') for name in
                            ('GITHUB_RUN_ID', 'GITHUB_RUN_ATTEMPT', 'GITHUB_SHA'))
    if not re.fullmatch(r'[0-9]+', run) or not re.fullmatch(r'[0-9]+', attempt) or not re.fullmatch(r'[0-9a-f]{40}', source):
        raise ValueError('Actual Actions run, attempt and source commit metadata required')
    return expected, run, attempt, source


def _read_evidence(run_dir):
    output = run_dir / 'output'
    film, verification = output / 'candidate-review.mp4', output / 'candidate-verification.json'
    if not film.is_file() or not verification.is_file():
        raise ValueError('Complete candidate MP4 and verification are required')
    report = json.loads(verification.read_text())
    duration = float(report.get('duration', float('nan')))
    if report.get('validated') is not True or report.get('decode') != 'PASS' or \
            not math.isfinite(duration) or not 120 <= duration < 180 or \
            (report.get('width'), report.get('height')) != (1080, 1920):
        raise ValueError('Complete decoded 1080x1920 review evidence is required')
    checksum = digest(film)
    if checksum != report.get('sha256'):
        raise ValueError('Candidate bytes changed after full media verification')
    generation_path = run_dir / 'generation-verification.json'
    generation = json.loads(generation_path.read_text()) if generation_path.is_file() else {}
    provenance_path = run_dir / 'professional_motion/delivery/narration.source.json'
    provenance = json.loads(provenance_path.read_text()) if provenance_path.is_file() else {}
    return film, {
        'complete_film_verified': True, 'video_sha256': checksum,
        'verification_sha256': digest(verification), 'duration': duration,
        'width': report['width'], 'height': report['height'], 'decode': report['decode'],
        'generation_report_present': generation_path.is_file(),
        'generation_report_sha256': digest(generation_path) if generation_path.is_file() else None,
        'generation_report_fresh_topic_claim': generation.get('fresh_topic_verified') is True,
        'generation_origin': report.get('generation_origin'),
        'fresh_topic_verified': report.get('fresh_topic_verified') is True,
        'narration_provenance': {key: provenance[key] for key in
            ('provider', 'voice', 'interaction_id', 'sha256', 'output_sha256') if key in provenance},
    }


def _safe_audit(path, profile):
    report = json.loads(Path(path).read_text())
    if not isinstance(report, dict) or report.get('profile') != profile or report.get('read_only') is not True:
        raise ValueError('A matching read-only repository audit report is required')
    def clean(value, posts=False):
        if isinstance(value, dict):
            return {key: clean(item, key == 'posts') for key, item in value.items()
                    if key in AUDIT_KEYS or (posts and key in {'youtube','facebook','instagram','tiktok'})}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        raise ValueError('Unsupported audit evidence value')
    return clean(report)


def export_review(profile, run_dir, stage, *, root='.', uploader_factory=None, store=None,
                  audit_report=None, status_branch=STATUS_BRANCH):
    if stage not in ('started', 'success', 'failure', 'cancelled'):
        raise ValueError('Unsupported review status stage')
    if status_branch not in STATUS_BRANCHES:
        raise ValueError('Only isolated review/audit status branches may be written')
    repository, run, attempt, source = context(profile)
    status = {'profile': profile, 'repository': repository, 'run_id': run,
              'run_attempt': attempt, 'source_commit': source, 'stage': stage,
              'requested_stage': stage, 'observed_at': datetime.now(timezone.utc).isoformat(),
              'review_only': True, 'automatically_published': False,
              'cutover_eligible': False, 'complete_film_verified': False, 'media_url': None}
    if audit_report is not None:
        status['kind'] = 'buffer_audit'
    else:
        status['credential_presence'] = {name: bool(os.getenv(name, '').strip()) for name in
            ('GEMINI_API_KEY', 'GEMINI_TEXT_API_KEY', 'GEMINI_TTS_API_KEY')}
        for filename, label in [('generation-failure.json', 'generation_failure'), ('generation-verification.json', 'generation_result')]:
            path = Path(run_dir) / filename
            if path.is_file():
                data = json.loads(path.read_text())
                allowed = {'slot', 'profile', 'topic_key', 'duration', 'story_sha256', 'audio_sha256',
                           'error_class', 'reservation_retained', 'publishable', 'fresh_topic_verified',
                           'legacy_film_not_used_as_fallback', 'failed_phase', 'measured_narration_seconds', 'timing_present'}
                status[label] = {key: value for key, value in data.items() if key in allowed}
    if stage != 'started':
        try:
            if audit_report is not None:
                status['buffer_audit'] = _safe_audit(audit_report, profile)
                status['audit_report_sha256'] = digest(audit_report)
            else:
                film, evidence = _read_evidence(Path(run_dir).resolve())
                status.update(evidence)
                if stage == 'success':
                    if not os.getenv('GITHUB_TOKEN', '').strip():
                        raise PermissionError('Repository release upload token is unavailable')
                    if uploader_factory is None:
                        from .release_media import ReviewReleaseUploader
                        uploader_factory = ReviewReleaseUploader
                    identity = f'v2-review-{profile}-{run}-{attempt}'
                    with media_identity(identity):
                        url = uploader_factory()._release_asset_url(film)
                    # The URL comes from the actual upload result, never a guessed release path.
                    from urllib.parse import urlsplit
                    parts = urlsplit(url) if isinstance(url, str) else None
                    if parts is None or parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
                        raise ValueError('Release uploader did not return a valid HTTPS media URL')
                    status['media_url'] = url
        except Exception as error:
            status['evidence_error_class'] = type(error).__name__
            if stage == 'success':
                status['stage'] = 'failure'
    try:
        commit = (store or StatusStore(root, status_branch)).save(run, attempt, status)
    except Exception as error:
        # Never print provider response/error bodies or credentials.
        status['status_persisted'] = False
        status['status_error_class'] = type(error).__name__
    else:
        status['status_persisted'] = True
        status['status_commit'] = commit
    return status


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=sorted(REPOSITORIES), required=True)
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--stage', choices=['started', 'success', 'failure', 'cancelled'], required=True)
    parser.add_argument('--audit-report', type=Path)
    parser.add_argument('--status-branch', choices=sorted(STATUS_BRANCHES), default=STATUS_BRANCH)
    args = parser.parse_args()
    try:
        result = export_review(args.profile, args.run_dir, args.stage,
                               audit_report=args.audit_report, status_branch=args.status_branch)
    except Exception as error:
        print(json.dumps({'status_persisted': False, 'error_class': type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['status_persisted'] or (args.stage == 'success' and result['stage'] != 'success'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
