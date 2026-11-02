import json,unittest
from unittest.mock import patch
from remotion_factory.publish import destinations,DestinationUnavailable,queued
from remotion_factory.health import check_posts,target_due,AuditFailure
from datetime import date

class ConnectionPreflight(unittest.TestCase):
 def call(self,disconnected=False,paused=False):
  cfg={'profile':'history','existing_bindings_confirmed_by_user':True,'buffer_channel_ids':{s:s for s in ('youtube','facebook','instagram')}}
  rows=[{'id':s,'service':s,'isQueuePaused':paused,'isDisconnected':disconnected} for s in cfg['buffer_channel_ids']]
  with patch('remotion_factory.publish.Path.read_text',return_value=json.dumps(cfg)),patch('remotion_factory.publish.query',side_effect=[{'account':{'organizations':[{'id':'org'}]}},{'channels':rows}]):return destinations('history')
 def test_current_three_connected_channels_pass(self):self.assertEqual(len(self.call()),3)
 def test_disconnected_channel_stops_before_paid_generation(self):
  with self.assertRaisesRegex(DestinationUnavailable,'refresh this channel'):self.call(disconnected=True)
 def test_unknown_connection_state_cannot_be_success(self):
  with self.assertRaises(DestinationUnavailable):self.call(disconnected=None)
 def test_paused_queue_stops(self):
  with self.assertRaises(DestinationUnavailable):self.call(paused=True)
 def test_audit_includes_error_posts_without_changing_publisher_queue_default(self):
  result={'posts':{'edges':[],'pageInfo':{'hasNextPage':False,'endCursor':None}}}
  with patch('remotion_factory.publish.query',return_value=result) as api:
   queued({'channel':'c','organization':'o'},'2026-11-03T15:00:00Z',include_errors=True);self.assertIn('sent,error]',api.call_args.args[0])
   queued({'channel':'c','organization':'o'},'2026-11-03T15:00:00Z');self.assertIn('sending,sent]',api.call_args.args[0])
 def test_provider_error_is_specific_and_private_links_are_redacted(self):
  rows={'youtube':[{'status':'error','error':{'message':'Authorization lost https://private.example/token-secret'}}]}
  with self.assertRaises(AuditFailure) as raised:check_posts({'youtube':{'channel':'c'}},rows,target_due(date(2026,11,3)),'postpublish')
  self.assertIn('Authorization lost',str(raised.exception));self.assertNotIn('token-secret',str(raised.exception))
