"""Topic-specific illustrations through Pollinations' unauthenticated Classic API.

No key, wallet, alternate host, or paid fallback is used. The authenticated API
is a separate product and must not silently replace this free experiment.
"""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import time
from urllib.parse import quote

import requests
from PIL import Image

ENDPOINT = 'https://image.pollinations.ai/prompt/'
MAX_BYTES = 12 * 1024 * 1024


def generated_illustration(scene, cache, *, timeout=60):
    prompt = str(scene.get('prompt', '')).strip()
    if not prompt:
        raise ValueError('A scene-specific image prompt is required')
    prompt += ' Editorial illustration only, never archival evidence. No captions or invented numerical labels.'
    digest = sha256(('classic-flux-v1:' + prompt).encode()).hexdigest()
    folder = Path(cache) / 'pollinations'
    folder.mkdir(parents=True, exist_ok=True)
    path, meta = folder / (digest[:24] + '.jpg'), folder / (digest[:24] + '.json')
    if path.exists() and meta.exists():
        record = json.loads(meta.read_text(encoding='utf-8'))
        if sha256(path.read_bytes()).hexdigest() == record.get('sha256'):
            return {**record, 'path': str(path), 'cached': True}
    seed = int(digest[:8], 16) % 2147483647
    url = ENDPOINT + quote(prompt[:4500], safe='')
    parameters = {'width': 768, 'height': 1344, 'model': 'flux', 'seed': seed}
    for attempt in range(2):
        try:
            with requests.get(url, params=parameters, timeout=(10, timeout), stream=True) as response:
                if response.status_code in (429, 502, 503, 504) and attempt == 0:
                    wait = max(8, float(response.headers.get('Retry-After', 8)))
                    if wait > 30:
                        raise RuntimeError('Pollinations requested deferred retry; task preserved')
                    time.sleep(wait)
                    continue
                if response.status_code != 200:
                    raise RuntimeError(f'Pollinations Classic HTTP {response.status_code}; no paid fallback')
                if not response.headers.get('Content-Type', '').lower().startswith('image/'):
                    raise RuntimeError('Pollinations returned a non-image response')
                data = bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise RuntimeError('Pollinations response exceeds image size limit')
            with Image.open(BytesIO(data)) as image:
                width, height = image.size
                image.verify()
            if width < 500 or height < 700:
                raise RuntimeError('Pollinations image is too small for the review composition')
            path.write_bytes(data)
            record = {'provider': 'Pollinations.ai Classic', 'model': 'flux', 'seed': seed,
                      'prompt': prompt, 'source_width': width, 'source_height': height,
                      'sha256': sha256(data).hexdigest(), 'generated': True,
                      'illustrative': True, 'archival_evidence': False,
                      'authenticated_api_used': False, 'paid_fallback_used': False}
            meta.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            return {**record, 'path': str(path), 'cached': False}
        except requests.RequestException:
            if attempt:
                raise RuntimeError('Pollinations Classic network failure; task preserved') from None
            time.sleep(8)
    raise RuntimeError('Pollinations Classic retry limit reached')
