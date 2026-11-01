from copy import deepcopy
import unittest
from production_v2.audit import audit_episode

class ReadOnlyAuditTests(unittest.TestCase):
    def setUp(self):
        self.mapping={'youtube':'a','facebook':'b','instagram':'c'}
        self.episode={'slot':'daily-2026-10-31','status':'scheduled','due_at':'2026-11-01T15:00:00Z','video_sha256':'a'*64,
                      'receipts':{key:{'id':'post-'+value,'status':'scheduled','media_url':'https://example.test/film.mp4'} for key,value in self.mapping.items()}}
    def test_missing_key_does_not_claim_retained_receipts_are_current(self):
        report=audit_episode(self.episode,self.mapping)
        self.assertFalse(report['live_verified'])
        self.assertTrue(all(not row['live_checked'] for row in report['posts'].values()))
    def test_current_observation_preserves_actual_due_and_sent_status(self):
        calls=[]
        before=deepcopy(self.episode)
        def query(text):
            calls.append(text)
            self.assertTrue(text.startswith('query '))
            identifier=next('post-'+value for value in self.mapping.values() if 'post-'+value in text)
            return {'post':{'id':identifier,'channelId':identifier[-1],'status':'sent','dueAt':'2026-11-01T15:00:00+00:00',
                            'sentAt':'2026-11-01T15:01:00Z','externalLink':'https://example.test/post',
                            'assets':[{'source':'https://example.test/film.mp4'}]}}
        report=audit_episode(self.episode,self.mapping,query)
        self.assertTrue(report['live_verified'])
        self.assertEqual(report['posts']['youtube']['status'],'sent')
        self.assertEqual(len(calls),3)
        self.assertEqual(self.episode,before)
    def test_missing_media_reference_never_becomes_verified(self):
        for receipt in self.episode['receipts'].values():receipt.pop('media_url')
        def query(text):
            identifier=next('post-'+value for value in self.mapping.values() if 'post-'+value in text)
            return {'post':{'id':identifier,'channelId':identifier[-1],'status':'scheduled','dueAt':self.episode['due_at'],'assets':[{'source':'https://example.test/other.mp4'}]}}
        self.assertFalse(audit_episode(self.episode,self.mapping,query)['live_verified'])

if __name__=='__main__':unittest.main()
