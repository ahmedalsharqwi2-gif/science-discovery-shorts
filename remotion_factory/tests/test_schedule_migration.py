"""No provider mutation may create a replacement or repeat an uncertain schedule edit."""
import unittest
from unittest.mock import patch
from remotion_factory.schedule_migration import move_one,edit_input

class ScheduleChanges(unittest.TestCase):
    """Exercise exact-ID edits, readback and uncertain-response recovery."""
    @staticmethod
    def call(before=None, record=None, error=None):
        """Run a schedule edit with independently mocked reads and mutation."""
        old={'id':'p','channelId':'c','status':'scheduled','dueAt':'2026-11-04T15:00:00Z','text':'keep','assets':[{'source':'original'}]}
        new={**old,'dueAt':'2026-11-04T10:00:00Z'}
        record={} if record is None else record
        with patch('remotion_factory.schedule_migration.read_post',side_effect=[before or old,new]),patch('remotion_factory.schedule_migration.query',side_effect=error,return_value={'editPost':{'post':{'id':'p'}}}) as api:
            result=move_one('youtube',{'channel':'c'},'p',{'source_due_at':old['dueAt'],'target_due_at':new['dueAt']},{'media_url':'original'},record,lambda:None)
            return result,api.call_args_list
    def test_same_id_uses_identical_retained_text_and_media(self):
        """Resubmit the exact retained content required by edit validation."""
        _,calls=self.call()
        self.assertEqual(calls[0].args[1]['input'],{'id':'p','mode':'customScheduled','dueAt':'2026-11-04T10:00:00Z','text':'keep','assets':[{'video':{'url':'original'}}]})
    def test_sent_or_wrong_owner_cannot_move(self):
        """Reject sent or foreign posts before a mutation is attempted."""
        for status in ('sent','sending','error'):
            with self.subTest(status=status),self.assertRaises(ValueError):
                self.call(before={'id':'p','channelId':'c','status':status})
    def test_uncertain_edit_is_not_resent(self):
        """Retain ambiguity rather than blindly retrying a write."""
        with self.assertRaisesRegex(ValueError,'Uncertain'):
            self.call(record={'phase':'uncertain'})
    def test_successful_unknown_response_is_reconciled_without_editing_again(self):
        """A readback at the approved time makes another mutation unnecessary."""
        post={'id':'p','channelId':'c','status':'scheduled','dueAt':'2026-11-04T10:00:00Z','text':'keep','assets':[{'source':'original'}]}
        _,calls=self.call(before=post,record={'phase':'uncertain'})
        self.assertEqual(calls,[])

    def test_youtube_edit_keeps_the_existing_required_title_and_settings(self):
        """Preserve required metadata while changing only the scheduled instant."""
        metadata={'title':'existing title','privacy':'public','madeForKids':False,'notifySubscribers':False,'category':{'categoryId':'27'}}
        result=edit_input('youtube','p',{'target_due_at':'2026-11-04T10:00:00Z'},{'metadata':metadata,'text':'unchanged','assets':[{'source':'original'}]})
        self.assertEqual(result['metadata']['youtube'],{'title':'existing title','privacy':'public','madeForKids':False,'notifySubscribers':False,'categoryId':'27'})
        self.assertEqual(result['text'],'unchanged');self.assertEqual(result['assets'],[{'video':{'url':'original'}}])

class ExactOwnerTime(unittest.TestCase):
    def validate(self,**updates):
        from datetime import datetime,timezone
        from remotion_factory.schedule_migration import validate_request
        req={'repository':'owner/repo','approved_by_owner':True,'source_due_at':'2026-11-09T15:00:00Z','target_due_at':'2026-11-04T12:45:00Z','owner_requested_local_time':'2026-11-04T14:45:00+02:00','expected_ledger_due_at':'2026-11-04T10:00:00Z','video_sha256':'original'}
        req.update(updates)
        with patch('remotion_factory.schedule_migration.datetime',wraps=datetime) as clock:
            clock.now.return_value=datetime(2026,11,4,12,30,tzinfo=timezone.utc)
            validate_request(req,'owner/repo','science',{'due_at':'2026-11-04T10:00:00Z','video_sha256':'original','profile':'science'})
    def test_exact_cairo_override_reconciles_known_ledger_time(self):
        self.validate()
    def test_different_explicit_time_is_rejected(self):
        with self.assertRaises(ValueError):
            self.validate(owner_requested_local_time='2026-11-04T15:45:00+02:00')
    def test_expired_time_is_not_rolled_forward(self):
        with self.assertRaises(ValueError):
            self.validate(target_due_at='2026-11-04T12:00:00Z',owner_requested_local_time='2026-11-04T14:00:00+02:00')
    def test_unexpected_ledger_change_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            self.validate(expected_ledger_due_at='2026-11-05T10:00:00Z')
