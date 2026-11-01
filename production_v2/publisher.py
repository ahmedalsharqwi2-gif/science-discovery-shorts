"""Provider-independent submit/reconcile protocol, deliberately not an API client.

The adapter must implement preflight(mapping), submit(...), and lookup(post_id).
A network timeout after submit leaves intent unresolved and requires explicit
provider reconciliation. This never promises exactly-once remote execution.
"""
from datetime import datetime, timezone
from urllib.parse import urlparse
from .schedule import require_future_due
from .ledger import Conflict


def schedule_three(ledger, slot, mapping, due, media_url, provider, *, now=None, persist=None):
    if not callable(persist):
        raise RuntimeError('A durable ledger persistence callback is required before remote mutations')
    if len(mapping) != 3 or len(set(mapping.values())) != 3 or not all(mapping.values()):
        raise ValueError('Exactly three distinct confirmed destination channel IDs required')
    if urlparse(media_url).scheme != 'https' or not urlparse(media_url).hostname:
        raise ValueError('HTTPS media URL required')
    require_future_due(due, now or datetime.now(timezone.utc))
    # Credential/connection failures before mutations may be safely retried.
    provider.preflight(mapping)
    result = {}
    for service, channel in mapping.items():
        intent = ledger.submission(slot, service)
        if intent and (intent['channel_id'] != channel or intent['media_url'] != media_url or
                       datetime.fromisoformat(intent['due_at'].replace('Z', '+00:00')) != datetime.fromisoformat(due.replace('Z', '+00:00'))):
            raise Conflict('Retry binding differs from retained submission intent')
        receipt = ledger.receipt(slot, service)
        if receipt:
            expected_due = datetime.fromisoformat(due.replace('Z', '+00:00'))
            receipt_due = datetime.fromisoformat(receipt['due_at'].replace('Z', '+00:00'))
            if receipt.get('channel_id') != channel or receipt.get('media_url') != media_url or receipt_due != expected_due:
                raise Conflict('Retry binding differs from preserved receipt')
            observed = provider.lookup(receipt['id'])
            result[service] = ledger.reconcile(slot, service, observed)
            persist(ledger)
            continue
        require_future_due(due, now or datetime.now(timezone.utc))
        acknowledged = ledger.acknowledged(slot, service)
        if acknowledged:
            observed = provider.lookup(acknowledged)
            result[service] = ledger.reconcile(slot, service, observed)
            persist(ledger)
            continue
        ledger.begin_submission(slot, service, channel, due, media_url)
        persist(ledger)
        accepted = provider.submit(channel_id=channel, due_at=due, media_url=media_url)
        if not isinstance(accepted, dict) or not accepted.get('id'):
            raise RuntimeError('Provider did not return a post ID; reconcile intent')
        ledger.acknowledge(slot, service, accepted['id'])
        persist(ledger)
        observed = provider.lookup(accepted['id'])
        result[service] = ledger.reconcile(slot, service, observed)
        persist(ledger)
    return result
