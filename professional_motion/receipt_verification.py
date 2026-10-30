"""Prove actual provider state and absolute due time before confirming a daily slot."""
from datetime import datetime,timezone
import json
from film_factory.publish import query

def verify_scheduled(receipts,mapping,due):
 if len(mapping)!=3 or set(receipts)!=set(mapping):raise ValueError('Exactly three destination receipts are required')
 expected=datetime.fromisoformat(due.replace('Z','+00:00'))
 verified={}
 for service,channel in mapping.items():
  receipt=receipts[service]
  if not receipt or not receipt.get('id'):raise ValueError('Missing real Buffer post ID')
  actual=query('query { post(input: {id: '+json.dumps(receipt['id'])+'}) { id channelId status dueAt sentAt externalLink } }')['post']
  actual_due=datetime.fromisoformat((actual.get('dueAt') or '').replace('Z','+00:00'))
  if actual.get('id')!=receipt['id'] or actual.get('channelId')!=channel or actual.get('status')!='scheduled' or abs((actual_due-expected).total_seconds())>1:
   raise ValueError('Buffer has not confirmed the requested scheduled post and due time')
  verified[service]={**receipt,'channel_id':channel,'scheduled_at':actual_due.isoformat(),'status':actual['status'],'verified_at':datetime.now(timezone.utc).isoformat()}
 return verified
