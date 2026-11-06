"""Bounded, licensed Commons images with actual metadata; never invented URLs.

v2 changes (owner review 2026-11-07):
  * ranking is topic-match first, then PIXELS, then aspect fit -- v1 returned the
    first equal-match hit, which was frequently the smallest thumbnail on the page;
  * hard resolution floor (620px short edge / 0.7MP) because the render panel is
    976x1012 inside a 1080-wide canvas -- a 267x440 file cannot fill it;
  * cache key carries a version salt so previously cached thumbnails are refetched;
  * search asks Commons for 12 candidates at 2600px wide instead of 8 at 1800px.
"""
import hashlib
import html
import io
import json
import re
from urllib.parse import urlparse

import requests
from PIL import Image

LICENSES = ('Public domain', 'CC0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC BY 4.0', 'CC BY 3.0')
HOSTS = {'upload.wikimedia.org', 'commons.wikimedia.org', 'thumb.wikimedia.org'}
HEADERS = {'User-Agent': 'ArabicDocumentaryFactory/2.0 (licensed educational video; source credits retained)'}

CACHE_VERSION = 'v2'
MIN_EDGE = 620
MIN_AREA = 700_000
MAX_BYTES = 14_000_000
MIME_OK = ('image/jpeg', 'image/png', 'image/webp')
STOPWORDS = {'the', 'and', 'file', 'jpg', 'png', 'jpeg', 'history', 'mystery', 'ancient',
             'with', 'from', 'its', 'photo', 'image', 'picture', 'museum', 'copy', 'scan'}


def clean(value):
    return re.sub(r'<[^>]*>', ' ', html.unescape(value or '')).strip()


def tokens(value):
    return {w for w in re.findall('[a-z0-9]+', value.lower()) if len(w) > 2 and w not in STOPWORDS}


def _ratio_score(w, h):
    """1.0 for square-ish, decaying for panoramas / very tall strips."""
    if not w or not h:
        return 0.0
    r = max(w, h) / min(w, h)
    if r <= 1.05:
        return 1.0
    if r <= 1.8:
        return 1.0 - (r - 1.05) / 0.75 * 0.35
    if r <= 2.6:
        return 0.5 - (r - 1.8) / 0.8 * 0.35
    return 0.05


def choose(query, pages):
    required = tokens(query)
    ranked = []
    for page in pages:
        info = (page.get('imageinfo') or [{}])[0]
        meta = info.get('extmetadata', {})
        license_name = clean(meta.get('LicenseShortName', {}).get('value', ''))
        if license_name not in LICENSES:
            continue
        title = page.get('title', '')
        desc = clean(meta.get('ImageDescription', {}).get('value', ''))
        # a title match is worth double: it names the subject, the description only mentions it
        matched = len(required & tokens(title)) * 2 + len(required & tokens(desc + ' ' + title))
        minimum = 1 if len(required) == 1 else min(2, len(required))
        if not required or matched < minimum:
            continue
        mime = info.get('mime', '').lower()
        if mime not in MIME_OK:
            continue
        w = info.get('thumbwidth') or info.get('width') or 0
        h = info.get('thumbheight') or info.get('height') or 0
        if w and h and (min(w, h) < MIN_EDGE or w * h < MIN_AREA):
            continue
        url = info.get('thumburl') or info.get('url', '')
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname not in HOSTS:
            continue
        score = matched * 10_000 + min(w * h, 9_000_000) / 1_000 + _ratio_score(w, h) * 400
        ranked.append((score, matched, w * h, w, h, page, info, meta, license_name, url))
    if not ranked:
        return None
    best = max(ranked, key=lambda r: (r[0], r[1], r[2]))
    _, matched, area, w, h, page, info, meta, license_name, url = best
    page_pageid = page.get('pageid')
    attribution = ('https://commons.wikimedia.org/?curid=' + str(page_pageid)
                   if isinstance(page_pageid, int) and page_pageid > 0 else info.get('descriptionurl'))
    return {
        'query': query,
        'title': page['title'],
        'url': url,
        'page': info.get('descriptionurl'),
        'attribution_url': attribution,
        'artist': clean(meta.get('Artist', {}).get('value', ''))[:400],
        'description': clean(meta.get('ImageDescription', {}).get('value', ''))[:1400],
        'license': license_name,
        'license_url': meta.get('LicenseUrl', {}).get('value'),
        'source_pixels': f'{w}x{h}',
        'match_score': matched,
        'representation': 'archival subject image; may show a different date, never claimed as footage of the narrated event',
    }


def resolve(query, cache):
    key = hashlib.sha256((CACHE_VERSION + '|' + query.casefold()).encode()).hexdigest()[:20]
    proof = cache / (key + '.json')
    image = cache / (key + '.jpg')
    if proof.exists():
        try:
            saved = json.loads(proof.read_text())
        except (OSError, ValueError):
            saved = {}
        else:
            if saved.get('available') and image.exists() and \
                    hashlib.sha256(image.read_bytes()).hexdigest() == saved.get('sha256'):
                return saved, image
            if saved and not saved.get('available'):
                return saved, None
    try:
        response = requests.get('https://commons.wikimedia.org/w/api.php', params={
            'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': query,
            'gsrnamespace': 6, 'gsrlimit': 12, 'prop': 'imageinfo',
            'iiprop': 'url|size|extmetadata|mime', 'iiurlwidth': 2600,
        }, headers=HEADERS, timeout=25)
        response.raise_for_status()
        selected = choose(query, list(response.json().get('query', {}).get('pages', {}).values()))
        if not selected:
            raise ValueError('No related, clearly licensed image at usable resolution')
        with requests.get(selected['url'], headers=HEADERS, timeout=40, stream=True) as stream:
            stream.raise_for_status()
            if urlparse(stream.url).hostname not in HOSTS:
                raise ValueError('Unexpected media redirect')
            parts, size = [], 0
            for part in stream.iter_content(65536):
                size += len(part)
                if size > MAX_BYTES:
                    raise ValueError('Image exceeds bounded size')
                parts.append(part)
        raw = b''.join(parts)
        with Image.open(io.BytesIO(raw)) as im:
            if min(im.size) < MIN_EDGE or im.size[0] * im.size[1] < MIN_AREA:
                raise ValueError('Image resolution below panel floor')
            if max(im.size) > 14000:
                raise ValueError('Image resolution outside bounds')
            im = im.convert('RGB')
            im.thumbnail((2600, 2600))
            im.save(image, quality=95)
        saved = {
            **selected,
            'available': True,
            'sha256': hashlib.sha256(image.read_bytes()).hexdigest(),
            'original_download_sha256': hashlib.sha256(raw).hexdigest(),
            'download_bytes': size,
            'stored_pixels': f'{Image.open(image).size[0]}x{Image.open(image).size[1]}',
            'alterations': 'JPEG conversion, crop, camera movement and color treatment; no fabricated event imagery',
        }
    except (requests.RequestException, ValueError, OSError) as exc:
        saved = {'query': query, 'available': False, 'reason': type(exc).__name__ + ': ' + str(exc)[:180]}
    proof.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n')
    return saved, (image if saved.get('available') else None)


def enrich(story, plan, public, delivery):
    cache = delivery / 'visual-assets'
    cache.mkdir(exist_ok=True, parents=True)
    evidence = []
    queries = {}
    profile = story['profile']
    for i, scene in enumerate(plan['scenes']):
        if scene.get('asset') or not scene.get('image_query') or profile == 'stickman':
            continue
        if scene.get('legacy_kind') == 'map' or scene['shot_type'] in (
                'reconstruction', 'chronology', 'macro', 'process', 'comparison', 'takeaway', 'workflow'):
            continue
        query = scene['image_query'].strip()
        if query not in queries and len(queries) >= 3:
            continue
        if query not in queries:
            queries[query] = resolve(query, cache)
        proof, image = queries[query]
        evidence.append({'scene': scene['id'], **proof})
        if image:
            name = 'identity-media/' + image.name
            target = public / name
            target.parent.mkdir(exist_ok=True, parents=True)
            target.write_bytes(image.read_bytes())
            scene.update(
                asset=name,
                asset_label=(proof.get('license_label') or
                             ((clean(proof.get('title', '')).strip('File:').rsplit('.', 1)[0]
                               + ' • ' + proof['license']).strip(' •'))),
                asset_representation=proof['representation'],
                asset_sha256=proof['sha256'],
            )
        else:
            scene['asset_unavailable'] = proof.get('reason', 'unknown')
            scene['representation'] = 'تصوّر توضيحي للموضوع • ليس توثيقًا مصورًا للحدث'
    return evidence
