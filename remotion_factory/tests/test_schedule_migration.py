"""No provider mutation may create a replacement or repeat an uncertain schedule edit."""
import unittest
from unittest.mock import patch
from remotion_factory.schedule_migration import move_one

class ScheduleChanges(unittest.TestCase):
    """Exercise exact-ID edits, readback and uncertain-response recovery."""
    def call(self, before=None, record=None, error=None):
        """Run a schedule edit with independently mocked reads and mutation."""
        old={'id':'p','channelId':'c','status':'scheduled','dueAt':'2026-11-04T15:00:00Z','text':'keep','assets':[{'source':'original'}]}
        new={**old,'dueAt':'2026-11-04T10:00:00Z'}
        record={} if record is None else record
        with patch('remotion_factory.schedule_migration.read_post',side_effect=[before or old,new]),patch('remotion_factory.schedule_migration.query',side_effect=error,return_value={'editPost':{'post':{'id':'p'}}}) as api:
            result=move_one('youtube',{'channel':'c'},'p',{'source_due_at':old['dueAt'],'target_due_at':new['dueAt']},{'media_url':'original'},record,lambda:None)
            return result,api.call_args_list
    def test_only_schedule_fields_are_sent_for_the_same_id(self):
        """Preserve text/media by never including them in the mutation."""
        _,calls=self.call()
        self.assertEqual(calls[0].args[1]['input'],{'id':'p','mode':'customScheduled','dueAt':'2026-11-04T10:00:00Z'})
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
