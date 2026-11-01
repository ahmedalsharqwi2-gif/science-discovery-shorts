"""Read-only cutover eligibility. Never activates workflows or deletes history.

Evidence contains local paths. Use only manifests produced and reviewed for this
checkout. An archived narration technical render cannot satisfy new-generation
acceptance, even if its new MP4 hash is unique.
"""
import hashlib
import json
from pathlib import Path
import subprocess
from .ledger import tokens
from .media import verify

PROFILES = ('science', 'horror', 'history', 'news', 'stickman')
CANDIDATE_CONFIG = {'version': 2, 'active_pipeline': 'legacy',
                    'candidate_pipeline': 'production_v2', 'automatic_cutover': False,
                    'acceptance_profiles': list(PROFILES)}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def check_profile(profile, evidence):
    if evidence.get('origin') != 'new_generation':
        raise ValueError('Archived/reused/demo media cannot satisfy full new-generation acceptance')
    root = Path(evidence['repo_root']).resolve()
    snapshot = evidence.get('legacy_snapshot')
    if not isinstance(snapshot, list):
        raise ValueError('Explicit pre-change legacy snapshot required')
    actual_paths = {p.relative_to(root).as_posix() for p in (root / 'state').rglob('*.json') if p.is_file()}
    actual_paths |= {name for name in ('topic_history.json', 'film_topics.json', 'professional_topics.json',
                                     'publication_receipts.json') if (root / name).is_file()}
    if {row['path'] for row in snapshot} != actual_paths:
        raise ValueError('Legacy snapshot must cover every retained historical JSON file')
    old_tokens = set()
    for row in snapshot:
        path = (root / row['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha256(path) != row['sha256']:
            raise ValueError('Legacy state changed or escaped checkout during migration')
        old_tokens.update(tokens(json.loads(path.read_bytes())))
    story_path = Path(evidence['story_path'])
    story_hash = sha256(story_path)
    story = json.loads(story_path.read_bytes())
    topic = story.get('topic_key', '').casefold().strip()
    if not topic or topic != evidence.get('topic_key', '').casefold().strip():
        raise ValueError('Exact authored story topic identity required')
    if ({token for token in tokens(story) if token[0] in ('topic', 'source')} | {('topic', topic)}) & old_tokens:
        raise ValueError('Topic was already reserved/produced in legacy history')
    voice = evidence.get('narration', {})
    if voice.get('provider') != 'gemini' or voice.get('voice') != 'Charon' or voice.get('story_sha256') != story_hash:
        raise ValueError('New Charon narration must be bound to the exact new story')
    if voice.get('origin') != 'new_generation' or not voice.get('provider_evidence_id'):
        raise ValueError('New TTS provider evidence required; archive extraction is insufficient')
    if sha256(voice['path']) != voice.get('sha256'):
        raise ValueError('Narration bytes differ from provider evidence')
    renderer = evidence.get('renderer', {})
    if renderer.get('pipeline') != 'v2' or not renderer.get('source_sha256'):
        raise ValueError('Exact v2 renderer source fingerprints required')
    for relative, expected in renderer['source_sha256'].items():
        source = (root / relative).resolve()
        if not source.is_relative_to(root) or not source.is_file() or sha256(source) != expected:
            raise ValueError('Renderer source changed after full-film acceptance')
    video = verify(evidence['video_path'])
    if video['sha256'] != evidence.get('video_sha256'):
        raise ValueError('Acceptance video changed after review')
    if ('video', video['sha256']) in old_tokens:
        raise ValueError('Previously produced MP4 cannot pass migration acceptance')
    review = evidence.get('review', {})
    if review.get('video_sha256') != video['sha256'] or review.get('visual') != 'PASS' or review.get('audio') != 'PASS' or not review.get('reviewed_by'):
        raise ValueError('Explicit visual and listening review bound to this video required')
    if evidence.get('profile') != profile or story.get('profile') != profile:
        raise ValueError('Channel identity does not match authored story and acceptance profile')
    return {'profile': profile, 'passed': True, 'video_sha256': video['sha256'],
            'story_sha256': story_hash, 'topic_key': topic, 'media': video}


def evaluate(manifest):
    evidence = manifest.get('profiles', {})
    results = {}
    for profile in PROFILES:
        try:
            if profile not in evidence:
                raise ValueError('Missing full-channel acceptance evidence')
            results[profile] = check_profile(profile, evidence[profile])
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            results[profile] = {'profile': profile, 'passed': False, 'reason': str(error)}
    return {'cutover_eligible': all(row['passed'] for row in results.values()),
            'active_pipeline': 'legacy', 'automatic_cutover': False, 'profiles': results,
            'next_step': 'Only after all channels pass, review an explicit workflow switch that disables every legacy trigger before enabling v2'}
