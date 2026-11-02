import unittest
from datetime import datetime,timezone
from professional_motion.daily_request import target
def utc(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
class DailyTargetTests(unittest.TestCase):
    def test_winter_and_summer_crons(self):
        for created,cron,due in [('2026-11-04T07:13:00Z','0 7 * * *','2026-11-05T15:00:00Z'),('2026-07-04T06:13:00Z','0 6 * * *','2026-07-05T14:00:00Z')]:
            result=target('science','owner/repo',utc(created),utc(created),event='schedule',cron=cron)
            self.assertEqual(result['due_at'],due)
            self.assertIsNone(target('science','owner/repo',utc(created),utc(created),event='schedule',cron='0 8 * * *'))
    def test_rerun_keeps_target_and_expired_target_fails(self):
        created=utc('2026-11-04T07:00:00Z')
        self.assertEqual(target('news','owner/repo',created,utc('2026-11-05T10:00:00Z'),event='workflow_dispatch')['due_at'],'2026-11-05T15:00:00Z')
        with self.assertRaises(ValueError):target('news','owner/repo',created,utc('2026-11-05T15:00:00Z'),event='workflow_dispatch')
    def test_midnight_and_dst_boundary(self):
        result=target('horror','owner/repo',utc('2026-10-29T07:00:00Z'),utc('2026-10-29T07:00:00Z'),event='workflow_dispatch')
        self.assertEqual(result['due_at'],'2026-10-30T15:00:00Z')
if __name__=='__main__':unittest.main()
