import json,unittest
from datetime import datetime,timezone
from unittest.mock import patch
from remotion_factory import health
class RetainedReceipts(unittest.TestCase):
 def test_direct_receipt_lookup_when_due_listing_is_empty(self):
  due=datetime(2026,11,4,10,tzinfo=timezone.utc)
  ledger={'episodes':{
   'today':{'due_at':due.isoformat(),'receipts':{'youtube':{'id':'retained','channel_id':'own'}}},
   'other':{'due_at':'2026-11-05T10:00:00Z','receipts':{'youtube':{'id':'other-day','channel_id':'own'}}},
   'foreign':{'due_at':due.isoformat(),'receipts':{'youtube':{'id':'foreign','channel_id':'another'}}}}}
  post={'id':'retained','channelId':'own','status':'sent','externalLink':'https://youtu.be/example'}
  with patch.object(health,'read_json',return_value=ledger),patch.object(health,'queued',return_value=[]),patch.object(health,'query',return_value={'post':post}) as query:
   self.assertEqual(health.live_posts({'youtube':{'channel':'own'}},due),{'youtube':[post]})
   self.assertEqual(query.call_count,1)
   self.assertIn('"retained"',query.call_args.args[0])
 def test_extra_queue_post_is_preserved_for_duplicate_detection(self):
  due=datetime(2026,11,4,10,tzinfo=timezone.utc)
  ledger={'episodes':{'today':{'due_at':due.isoformat(),'receipts':{'youtube':{'id':'retained','channel_id':'own'}}}}}
  def lookup(text):
   identifier='extra' if '"extra"' in text else 'retained'
   return {'post':{'id':identifier,'channelId':'own'}}
  with patch.object(health,'read_json',return_value=ledger),patch.object(health,'queued',return_value=[{'id':'extra'},{'id':'retained'}]),patch.object(health,'query',side_effect=lookup) as query:
   rows=health.live_posts({'youtube':{'channel':'own'}},due)
   self.assertEqual({p['id'] for p in rows['youtube']},{'extra','retained'})
   self.assertEqual(query.call_count,2)
