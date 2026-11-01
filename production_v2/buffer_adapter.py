"""Dormant Buffer adapter using only the current repository's existing secret.

No API call occurs at construction. Publication requires an explicit validated
cutover, exact retained channel bindings, and the durable schedule_three protocol.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from .schedule import require_future_due

REPOSITORIES = {
    'science': 'science-discovery-shorts', 'horror': 'arabic-horror-stories',
    'history': 'documented-history-stories', 'news': 'ai-news-daily',
}
PROFILES = {'science', 'horror', 'history', 'news', 'stickman'}
SERVICES = {'youtube', 'facebook', 'instagram', 'tiktok'}


class BufferAdapter:
    def __init__(self, profile, root='.', *, title, caption, client=None, query=None, clock=None):
        if profile not in REPOSITORIES:
            raise ValueError('Unsupported repository publishing profile')
        self.profile, self.root = profile, Path(root).resolve()
        self.repository = 'ahmedalsharqwi2-gif/' + REPOSITORIES[profile]
        self.title, self.caption = title, caption
        self._client, self._query = client, query
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.mapping = None
        self._preflight_passed = False
        if client is not None:
            client.schedule_mode = 'customScheduled'

    def _context(self):
        if os.getenv('GITHUB_REPOSITORY') != self.repository:
            raise PermissionError('Use the matching repository Actions context and its own Buffer secret')
        if not os.getenv('BUFFER_API_KEY', '').strip():
            raise PermissionError('The matching repository Buffer secret is unavailable')

    def _active(self):
        config = json.loads((self.root / 'config/production_v2.json').read_text())
        if config.get('profile') != self.profile or config.get('active_pipeline') != 'production_v2':
            raise PermissionError('Production v2 has not passed cutover; submissions remain disabled')
        report_path = self.root / 'config/production_v2_acceptance.json'
        if not report_path.is_file():
            raise PermissionError('Full-channel cutover evidence is absent')
        raw = report_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != config.get('acceptance_report_sha256'):
            raise PermissionError('Cutover acceptance evidence changed or is not fingerprinted')
        report = json.loads(raw)
        rows = report.get('profiles', {})
        if report.get('cutover_eligible') is not True or set(rows) != PROFILES or not all(
                rows[name].get('passed') is True for name in PROFILES):
            raise PermissionError('All five complete channel films must pass before submission')

    def _bindings(self):
        config = json.loads((self.root / 'config/professional_destinations.json').read_text())
        mapping = config.get('buffer_channel_ids', {})
        if config.get('profile') != self.profile or config.get('existing_bindings_confirmed_by_user') is not True:
            raise PermissionError('User-confirmed repository channel bindings are required')
        if not isinstance(mapping, dict) or len(mapping) != 3 or not set(mapping) <= SERVICES or \
                len(set(mapping.values())) != 3 or not all(isinstance(value, str) and value for value in mapping.values()):
            raise ValueError('Exactly three distinct retained Buffer destination IDs required')
        return mapping

    def _read(self, text):
        self._context()
        if self._query is None:
            from film_factory.publish import query
            self._query = query
        try:
            return self._query(text)
        except Exception:
            # Provider errors may include request details; never echo credential values.
            raise ConnectionError('Buffer read failed; retained evidence must be reconciled') from None

    def preflight(self, mapping):
        self._preflight_passed = False
        self._active()
        self._context()
        expected = self._bindings()
        if mapping != expected:
            raise ValueError('Requested destinations differ from retained user-confirmed bindings')
        organizations = self._read('query { account { organizations { id } } }')['account']['organizations']
        channels = []
        for organization in organizations:
            channels.extend(self._read('query { channels(input: {organizationId: ' + json.dumps(organization['id']) +
                                       '}) { id service isQueuePaused } }')['channels'])
        for service, identifier in expected.items():
            found = [row for row in channels if row.get('id') == identifier]
            if len(found) != 1 or found[0].get('service', '').lower() != service or found[0].get('isQueuePaused') is not False:
                raise PermissionError('A retained destination is missing, paused or connected to a different service')
        self.mapping = expected
        self._preflight_passed = True
        return dict(expected)

    def submit(self, *, channel_id, due_at, media_url):
        self._active()
        self._context()
        if not self._preflight_passed or self.mapping != self._bindings():
            raise PermissionError('Exact current repository destination preflight is required')
        if channel_id not in self.mapping.values():
            raise ValueError('Channel ID is not a retained repository destination')
        require_future_due(due_at, self.clock())
        parts = urlsplit(media_url)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password:
            raise ValueError('An explicit HTTPS video URL is required')
        if not self.title.strip() or not self.caption.strip():
            raise ValueError('The current authored film title and caption are required')
        if self._client is None:
            from film_factory.buffer import ContentPublisher
            self._client = ContentPublisher()
        # Never invoke release uploads, queue mode, direct YouTube or blanket retries.
        self._client.schedule_mode = 'customScheduled'
        service = next(service for service, identifier in self.mapping.items() if identifier == channel_id)
        try:
            result = self._client._create_buffer_post(channel_id=channel_id, text=self.caption,
                media_url=media_url, due_at=due_at, service=service, title=self.title, facebook_type='reel')
        except Exception:
            raise RuntimeError('Buffer submission outcome is uncertain; reconcile the persisted intent before retrying') from None
        if not isinstance(result, dict) or not result.get('id'):
            raise RuntimeError('Buffer did not return a post ID; reconcile the persisted intent')
        return result

    def lookup(self, post_id):
        self._context()
        row = self._read('query { post(input: {id: ' + json.dumps(post_id) +
                         '}) { id channelId status dueAt assets {source} } }')['post']
        sources = [asset.get('source') for asset in row.get('assets', [])]
        if row.get('id') != post_id or len(sources) != 1 or not isinstance(sources[0], str) or not sources[0]:
            raise ValueError('Provider lookup did not prove one exact post and media URL')
        due = datetime.fromisoformat((row.get('dueAt') or '').replace('Z', '+00:00'))
        if due.tzinfo is None:
            raise ValueError('Provider due time must be absolute')
        return {'id': row['id'], 'channel_id': row.get('channelId'), 'status': row.get('status'),
                'due_at': row['dueAt'], 'media_url': sources[0]}
