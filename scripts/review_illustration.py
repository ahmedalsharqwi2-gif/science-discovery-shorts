"""Reuse one existing review image only for its exact approved narration."""
from hashlib import sha256
import json
from pathlib import Path


def approved_illustration(episode, root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[1]
    folder = root / 'review'
    record = json.loads((folder / 'propeller-illustration.json').read_text(encoding='utf-8'))
    if sha256(episode.get('narration', '').encode()).hexdigest() != record['narration_sha256']:
        raise RuntimeError('Review illustration belongs to another narration')
    path = folder / record['file']
    if path.parent != folder or sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise RuntimeError('Review illustration integrity check failed')
    return {**record, 'path': str(path), 'cached': True,
            'single_topic_image_reused': True, 'new_api_request_used': False}
