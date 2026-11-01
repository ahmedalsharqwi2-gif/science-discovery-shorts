"""Read only an existing Actions run's bounded diagnostics; never rerun providers."""
from datetime import datetime, timezone
import io
import json
import os
from pathlib import PurePosixPath
import re
import zipfile
from .export_review import context, StatusStore, REPOSITORIES

BRANCH = 'codex/production-v2-diagnostics'
MAX_DOWNLOAD = 16 * 1024 * 1024
MAX_FILE = 512 * 1024
MAX_MEMBERS = 200
JSON_NAMES = {'planning-errors.json', 'candidate-status.json', 'generation-failure.json', 'error.json'}
JSON_KEYS = {'topic_key', 'error_class', 'validation', 'profile', 'slot', 'reservation_retained',
             'failed_phase', 'measured_narration_seconds', 'timing_present', 'already_reserved',
             'key', 'title', 'family', 'variant', 'published', 'publishable'}
ACTIONABLE = re.compile(r'RuntimeError|ValueError|KeyError|BudgetExceeded|HTTP\s*\d{3}|Error:|Exception:|No usable|quota|source bank|Traceback', re.I)


def redact(value):
    text = str(value)
    secrets = [value for name, value in os.environ.items()
               if re.search(r'KEY|TOKEN|SECRET', name, re.I) and value and len(value) >= 4]
    for secret in sorted(set(secrets), key=len, reverse=True):
        text = text.replace(secret, '[REDACTED]')
    text = re.sub(r'(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)[^\s,;]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)([?&](?:key|api_key|token|access_token)=)[^\s&#]+', r'\1[REDACTED]', text)
    text = re.sub(r'(?i)\b(?:ghp_|github_pat_)[A-Za-z0-9_]+', '[REDACTED]', text)
    text = re.sub(r'AIza[A-Za-z0-9_-]{20,}', '[REDACTED]', text)
    return text


def _clean_json(value, depth=0):
    if depth > 8:
        return '[depth bounded]'
    if isinstance(value, dict):
        return {key: _clean_json(item, depth+1) for key, item in value.items() if key in JSON_KEYS}
    if isinstance(value, list):
        return [_clean_json(item, depth+1) for item in value[:100]]
    if isinstance(value, str):
        return redact(value)[:500]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return None


def inspect_zip(raw, *, logs=False):
    evidence = []
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = archive.infolist()
        if len(members) > MAX_MEMBERS:
            raise ValueError('Diagnostic archive member count exceeds limit')
        consumed = 0
        for member in members:
            path = PurePosixPath(member.filename.replace('\\', '/'))
            if not path.parts or path.is_absolute() or '..' in path.parts or ':' in path.parts[0]:
                raise ValueError('Unsafe archive path rejected')
            if member.is_dir():
                continue
            eligible = path.suffix == '.txt' if logs else path.name in JSON_NAMES
            if not eligible:
                continue
            if member.file_size > MAX_FILE:
                evidence.append({'file': redact(str(path)), 'omitted': 'file_size_limit'})
                continue
            with archive.open(member) as stream:
                content = stream.read(MAX_FILE + 1)
            consumed += len(content)
            if len(content) > MAX_FILE or consumed > 4 * 1024 * 1024:
                raise ValueError('Diagnostic archive expanded size exceeds limit')
            if logs:
                lines = [redact(line)[:500] for line in content.decode('utf-8', 'replace').splitlines()
                         if ACTIONABLE.search(line)]
                if lines:
                    evidence.append({'file': redact(str(path)), 'error_lines': lines[-60:]})
            else:
                evidence.append({'file': redact(str(path)), 'data': _clean_json(json.loads(content))})
    return evidence


class Reader:
    def __init__(self, repository, token, *, session=None):
        if not token:
            raise PermissionError('Repository Actions read token unavailable')
        if session is None:
            import requests
            session = requests.Session()
        self.session = session
        self.base = 'https://api.github.com/repos/' + repository
        self.headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'}

    def json(self, path):
        response = self.session.get(self.base + path, headers=self.headers, timeout=45)
        if response.status_code != 200:
            raise RuntimeError('GitHub diagnostic read HTTP ' + str(response.status_code))
        return response.json()

    def archive(self, path):
        # Do not forward the repository token to signed object storage URLs.
        response = self.session.get(self.base + path, headers=self.headers, timeout=60,
                                    allow_redirects=False, stream=True)
        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get('Location', '')
            from urllib.parse import urlsplit
            parsed = urlsplit(location)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Unsafe diagnostic redirect')
            response.close()
            response = self.session.get(location, timeout=60, stream=True)
        if response.status_code != 200:
            response.close()
            raise RuntimeError('GitHub diagnostic archive HTTP ' + str(response.status_code))
        result = bytearray()
        try:
            for chunk in response.iter_content(64 * 1024):
                result.extend(chunk)
                if len(result) > MAX_DOWNLOAD:
                    raise ValueError('Diagnostic download exceeds limit')
        finally:
            response.close()
        return bytes(result)


def diagnose(profile, target_run, *, root='.', reader=None, store=None):
    if not re.fullmatch(r'[0-9]+', str(target_run)):
        raise ValueError('An explicit numeric prior run ID is required')
    repository, run, attempt, source = context(profile)
    reader = reader or Reader(repository, os.getenv('GITHUB_TOKEN', ''))
    result = {'profile': profile, 'repository': repository, 'kind': 'read_only_diagnostic',
              'stage': 'success', 'run_id': run, 'run_attempt': attempt,
              'source_commit': source, 'target_run': str(target_run),
              'observed_at': datetime.now(timezone.utc).isoformat(),
              'no_provider_calls': True, 'no_posts_created': True, 'evidence': [], 'errors': []}
    def error_info(stage, error):
        row = {'stage': stage, 'error_class': type(error).__name__}
        match = re.search(r'HTTP\s*(\d{3})', str(error))
        if match:
            row['http_status'] = int(match.group(1))
        return row
    try:
        artifacts = reader.json('/actions/runs/' + str(target_run) + '/artifacts?per_page=100').get('artifacts', [])
        for artifact in artifacts[:10]:
            identifier = str(artifact.get('id', ''))
            if artifact.get('expired') or not identifier.isdigit():
                continue
            try:
                result['evidence'].extend(inspect_zip(reader.archive('/actions/artifacts/' + identifier + '/zip')))
            except Exception as error:
                result['errors'].append(error_info('artifact', error))
    except Exception as error:
        result['errors'].append(error_info('artifact_listing', error))
    try:
        result['evidence'].extend(inspect_zip(reader.archive('/actions/runs/' + str(target_run) + '/logs'), logs=True))
    except Exception as error:
        result['errors'].append(error_info('logs', error))
    serialized = json.dumps(result['evidence'], ensure_ascii=False)
    result['provider_http_statuses'] = sorted(set(int(code) for code in re.findall(r'HTTP\s*(\d{3})', serialized)))
    if not result['evidence']:
        result['stage'] = 'failure'
    commit = (store or StatusStore(root, BRANCH)).save(run, attempt, result)
    result['status_commit'] = commit
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=sorted(REPOSITORIES), required=True)
    parser.add_argument('--target-run', required=True)
    args = parser.parse_args()
    try:
        result = diagnose(args.profile, args.target_run)
    except Exception as error:
        print(json.dumps({'error_class': type(error).__name__, 'read_only': True}))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result['stage'] != 'success':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
