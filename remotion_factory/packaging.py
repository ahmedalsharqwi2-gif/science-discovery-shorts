"""Prepare episode-bound titles and cover proofs without a new provider call."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

VERSION = 1
COVER_FRAME = 6
OPENING_FRAMES = 18
FPS = 30


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean_title(value):
    if not isinstance(value, str):
        raise ValueError('Publication title must be text, never a JSON object or array')
    title = ' '.join(unicodedata.normalize('NFKC', value).split()).strip()
    if title.startswith(('[', '{')) or re.search(r'[\[\]{}]', title):
        raise ValueError('Publication title contains serialized JSON')
    title = re.sub(r'^(?:اسرار الكون|أسرار الكون|نقص ونرو[يى]|ملفات غامض[ةه]|ai على السريع|إفترض كده|افترض كده)\s*[|:—–]\s*', '', title, flags=re.I)
    if not 5 <= len(title) <= 100 or len(title.split()) < 2:
        raise ValueError('Publication title must be complete and fit YouTube without truncation')
    if not re.search(r'[\u0621-\u064a]', title):
        raise ValueError('Arabic publication title required')
    if any(unicodedata.category(c) in ('Cc', 'Cs') for c in title):
        raise ValueError('Publication title contains control characters')
    return title


def locked_public_title(value,profile):
    from visual_contract import load_template
    t=load_template()
    if profile!=t['channel']:raise ValueError('Cross-channel publication title')
    prefix=t.get('public_title_prefix','')
    raw=value[len(prefix):] if prefix and value.startswith(prefix) else value
    title=prefix+clean_title(raw)
    if len(title)>100:raise ValueError('Publication title exceeds 100 characters; rewrite, never truncate')
    return title


def metadata(story, story_digest):
    title = clean_title(story.get('title'))
    cover = story.get('cover_text') or title
    cover = clean_title(cover)
    if story.get('cover_text') and (len(cover) > 48 or len(cover.split()) > 6):
        raise ValueError('Authored cover heading must fit a phone: at most six words')
    # Retained episodes keep their whole title; never invent a new claim or cut it.
    if len(cover) > 100:
        raise ValueError('Cover heading is too long')
    extra={}
    if story.get('visual_template_version')==1:
        title=locked_public_title(title,story['profile']);extra['visual_template_version']=1
    return {**extra,'version': VERSION, 'profile': story['profile'], 'title': title,
            'cover_text': cover, 'story_sha256': story_digest,
            'cover_file': 'cover.png', 'cover_frame': COVER_FRAME,
            'cover_offset_ms': COVER_FRAME * 1000 // FPS,
            'opening_frames': OPENING_FRAMES, 'fps': FPS,
            'selection_supported': {'instagram': True, 'youtube': False, 'facebook': False}}


def verify(root, report):
    """Legacy retained movies are unchanged; new covers require exact byte bindings."""
    root = Path(root)
    renderer = report.get('renderer', {})
    proof = report.get('publication')
    if not proof:
        if renderer.get('publication_sha256'):
            raise ValueError('Publication proof missing from a packaged render')
        return None
    package_file = root / 'publication.json'
    if sha(package_file) != renderer.get('publication_sha256'):
        raise ValueError('Publication metadata changed after rendering')
    package = json.loads(package_file.read_text())
    if package != proof or package['story_sha256'] != report['story_sha256'] or package['profile'] != report['profile']:
        raise ValueError('Publication package belongs to another episode')
    if package.get('cover_file') != 'cover.png' or sha(root / 'cover.png') != renderer.get('cover_sha256'):
        raise ValueError('Cover image changed after rendering')
    canonical=locked_public_title(package['title'],package['profile']) if package.get('visual_template_version')==1 else clean_title(package['title'])
    if canonical != package['title'] or clean_title(package['cover_text']) != package['cover_text']:
        raise ValueError('Publication text is not canonical')
    if (package.get('version'), package.get('cover_frame'), package.get('cover_offset_ms'), package.get('opening_frames'), package.get('fps')) != (VERSION, COVER_FRAME, 200, OPENING_FRAMES, FPS):
        raise ValueError('Cover frame does not match the rendered opening')
    from PIL import Image
    with Image.open(root / 'cover.png') as image:
        if image.size != (1080, 1920):
            raise ValueError('Cover must use the actual portrait film geometry')
    return package


def video_asset(url, service, package=None):
    video = {'url': url}
    if service == 'instagram' and package:
        video['metadata'] = {'thumbnailOffset': package['cover_offset_ms']}
    return {'video': video}
