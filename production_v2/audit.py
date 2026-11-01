"""Read-only current Buffer observations, separated from retained local receipts."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path


def instant(value):
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timezone-aware provider timestamp required')
    return result


def audit_episode(episode, mapping, query=None):
    result = {'slot': episode.get('slot'), 'video_sha256': episode.get('video_sha256'),
              'retained_status': episode.get('status'), 'due_at': episode.get('due_at'),
              'live_verified': False, 'posts': {}, 'no_posts_created': True}
    receipts = episode.get('receipts', {})
    if len(mapping) != 3 or set(receipts) != set(mapping):
        result['problem'] = 'Exactly three retained destination receipts required'
        return result
    for service, channel in mapping.items():
        receipt = receipts[service]
        row = {'retained_post_id': receipt.get('id'), 'expected_channel_id': channel,
               'retained_status': receipt.get('status'), 'live_checked': False}
        result['posts'][service] = row
        if query is None:
            row['problem'] = 'BUFFER_API_KEY or allowed API access unavailable; retained status is not current proof'
            continue
        if not receipt.get('id'):
            row['problem'] = 'Retained receipt has no provider post ID'
            continue
        try:
            data = query('query { post(input: {id: ' + json.dumps(receipt['id']) +
                         '}) { id channelId status dueAt sentAt externalLink assets {source} } }')['post']
            sources = [asset.get('source') for asset in data.get('assets', [])]
            expected_media = (episode.get('media_correction', {}).get('media_url') or receipt.get('media_url'))
            due_matches = instant(data['dueAt']) == instant(episode['due_at'])
            row.update(live_checked=True, observed_post_id=data.get('id'), channel_id=data.get('channelId'),
                       status=data.get('status'), scheduled_at=data.get('dueAt'), sent_at=data.get('sentAt'),
                       external_link=data.get('externalLink'), media_urls=sources,
                       post_and_channel_match=data.get('id') == receipt['id'] and data.get('channelId') == channel,
                       due_matches=due_matches,
                       media_matches=expected_media in sources if expected_media else None)
            row['verified'] = row['post_and_channel_match'] and due_matches and row['media_matches'] is True
            if expected_media is None:
                row['problem'] = 'Expected media URL not retained; identity/time observed, media not independently matched'
        except Exception as error:
            row['error_class'] = type(error).__name__
    result['live_verified'] = all(row.get('verified') is True for row in result['posts'].values())
    return result


def retained_report(root, query=None):
    root = Path(root)
    config = json.loads((root / 'config/professional_destinations.json').read_text())
    mapping = config['buffer_channel_ids']
    registry = json.loads((root / 'state/professional_topics.json').read_text())
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'profile': config['profile'],
            'read_only': True, 'live_access_available': query is not None,
            'episodes': [audit_episode(episode, mapping, query) for episode in registry['episodes'] if episode.get('receipts')]}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    parser.add_argument('--live', action='store_true', help='Use only this repository Actions secret; never a shared local key')
    args = parser.parse_args()
    query = None
    if args.live:
        profile = json.loads((Path(args.root) / 'config/professional_destinations.json').read_text())['profile']
        repo = {'science':'science-discovery-shorts','horror':'arabic-horror-stories','history':'documented-history-stories','news':'ai-news-daily'}[profile]
        if os.getenv('GITHUB_REPOSITORY') != 'ahmedalsharqwi2-gif/' + repo:
            parser.error('Live audit must run in the matching repository Actions context with its own BUFFER_API_KEY secret')
        if os.getenv('BUFFER_API_KEY'):
            from film_factory.publish import query
    report = retained_report(args.root, query)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({'profile': report['profile'], 'episodes': len(report['episodes']),
                      'live_access_available': report['live_access_available'], 'report': str(target)}, indent=2))


if __name__ == '__main__':
    main()
