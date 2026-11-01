"""Read-only probes of requested official source pages; never infer geometry."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit, urljoin, parse_qsl
from .export_review import context, StatusStore

BRANCH = 'codex/production-v2-sources'
MAX_BYTES = 3 * 1024 * 1024
MAX_PAGES = 12
KEYWORDS = re.compile(r'\btier|\bstorey|\bstory|\barch(?:es)?\b|amphitheat|\bcanal\b|\btrough\b|\bpier|colosseum|pontcysyllte', re.I)


def scope(url):
    value = urlsplit(url)
    host = (value.hostname or '').lower()
    if value.scheme != 'https' or value.username or value.password or value.port not in (None, 443):
        raise ValueError('An explicit HTTPS official URL without credentials is required')
    if any(re.search(r'key|token|secret|authorization', key, re.I) for key, _ in parse_qsl(value.query)):
        raise ValueError('Keyless public source URLs are required')
    if host == 'whc.unesco.org':
        return 'whc.unesco.org'
    if host in ('colosseo.it', 'www.colosseo.it'):
        return 'colosseo.it'
    if host == 'nasa.gov' or host.endswith('.nasa.gov'):
        return 'nasa.gov'
    raise ValueError('Source host is not an approved official authority')


def quotations(text):
    """Select at most six nonoverlapping 15-word excerpts, no more than90words."""
    words = text.split()
    selected, claimed = [], set()
    for index, word in enumerate(words):
        if not KEYWORDS.search(word):
            continue
        start = max(0, min(index - 5, len(words) - 15))
        end = min(len(words), start + 15)
        indices = set(range(start, end))
        if claimed & indices:
            continue
        phrase = ' '.join(words[start:end])
        if phrase:
            selected.append(phrase)
            claimed.update(indices)
        if len(selected) == 6:
            break
    return selected


def extract_page(raw, url):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw, 'html.parser')
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    canonical = None
    link = soup.find('link', rel=lambda value: value and 'canonical' in value)
    if link and link.get('href'):
        candidate = urljoin(url, link['href'])
        if scope(candidate) == scope(url):
            canonical = candidate
    for node in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        node.decompose()
    body = soup.find('article') or soup.find('main') or soup.body or soup
    text = ' '.join(body.stripped_strings)
    excerpts = quotations(text)
    return {'title': title[:300], 'canonical_url': canonical, 'body_word_count': len(text.split()),
            'evidence_sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(),
            'excerpts': excerpts, 'quoted_words': sum(len(row.split()) for row in excerpts),
            'geometry_inference': None,
            'geometry_note': 'No tier count or geometry is inferred. Any contract must cite an explicit source statement.'}


def probe(url, *, session=None):
    authority = scope(url)
    if session is None:
        import requests
        session = requests.Session()
    current = url
    result = {'requested_url': url, 'authority': authority, 'verified': False,
              'tls_verification': True, 'keyless_get_only': True}
    for _ in range(6):
        if scope(current) != authority:
            raise ValueError('Redirect left the requested official authority scope')
        response = session.get(current, headers={'User-Agent': 'VideoFactorySourceProbe/2.0'},
                               timeout=45, allow_redirects=False, stream=True, verify=True)
        status = response.status_code
        if status in (301, 302, 303, 307, 308):
            target = urljoin(current, response.headers.get('Location', ''))
            response.close()
            if scope(target) != authority:
                raise ValueError('Official source redirected outside its authority scope')
            current = target
            continue
        result.update(final_url=current, http_status=status)
        if status != 200:
            response.close()
            result['problem'] = 'Official page did not return HTTP200; no substitute facts were generated'
            return result
        content_type = response.headers.get('Content-Type', '').lower()
        if content_type and 'html' not in content_type:
            response.close()
            result['problem'] = 'Expected an official HTML article; no content inferred'
            return result
        content = bytearray()
        try:
            for chunk in response.iter_content(64 * 1024):
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise ValueError('Official page exceeds bounded evidence download size')
        finally:
            response.close()
        result.update(extract_page(bytes(content), current))
        result['verified'] = bool(result['title'] and result['body_word_count'] >= 50)
        if not result['verified']:
            result['problem'] = 'Official response lacks sufficient readable article text'
        return result
    raise ValueError('Official redirect chain exceeded limit')


def request_urls(path, profile):
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        if data.get('profile') not in (None, profile):
            raise ValueError('Source request belongs to another channel')
        values = data.get('urls')
    else:
        values = data
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_PAGES or not all(isinstance(url, str) for url in values):
        raise ValueError('Supply a bounded list of one to12 explicit official URLs')
    if len(set(values)) != len(values):
        raise ValueError('Duplicate source URLs in request')
    for url in values:
        scope(url)
    return values


def run(profile, request, *, root='.', session=None, store=None):
    repository, run_id, attempt, source = context(profile)
    urls = request_urls(request, profile)
    report = {'profile': profile, 'repository': repository, 'run_id': run_id, 'run_attempt': attempt,
              'source_commit': source, 'kind': 'official_source_probe', 'stage': 'success',
              'observed_at': datetime.now(timezone.utc).isoformat(), 'read_only': True,
              'no_provider_calls': True, 'no_posts_created': True, 'sources': []}
    quoted_sources, quoted_content = set(), set()
    for url in urls:
        try:
            row = probe(url, session=session)
        except Exception as error:
            row = {'requested_url': url, 'verified': False, 'error_class': type(error).__name__,
                   'geometry_inference': None}
        if row.get('verified'):
            canonical = urlsplit(row.get('canonical_url') or row['final_url'])
            identity = canonical._replace(query='', fragment='', path=canonical.path.rstrip('/')).geturl()
            content_identity = (row['authority'], row['evidence_sha256'])
            if identity in quoted_sources or content_identity in quoted_content:
                row.update(excerpts=[], quoted_words=0, duplicate_source_evidence=True)
            quoted_sources.add(identity)
            quoted_content.add(content_identity)
        report['sources'].append(row)
    report['all_requested_pages_verified'] = all(row.get('verified') for row in report['sources'])
    report['status_commit'] = (store or StatusStore(root, BRANCH)).save(run_id, attempt, report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=['science', 'horror', 'history', 'news', 'stickman'], required=True)
    parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.profile, args.request)
    except Exception as error:
        print(json.dumps({'read_only': True, 'error_class': type(error).__name__}))
        raise SystemExit(1)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result['all_requested_pages_verified']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
