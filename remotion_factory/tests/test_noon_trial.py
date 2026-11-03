"""Civil-time regressions for previous-evening production and noon release."""
import unittest
from datetime import date, datetime, timezone
from remotion_factory.schedule import hours,due_for,production_at,audit_day
from remotion_factory.daily import slot_for
from remotion_factory.health import clock_source
class NoonTrial(unittest.TestCase):
    """Keep production dates, release dates and clock provenance distinct."""
    def test_trial_boundaries_and_previous_evening(self):
        """Verify trial boundaries and previous evening."""
        self.assertEqual(hours(date(2026,11,3)),(9,17))
        for day in (date(2026,11,4),date(2026,11,17)):
            self.assertEqual(hours(day),(19,12))
            self.assertEqual(production_at(day).hour,19)
            self.assertEqual((due_for(day)-production_at(day)).total_seconds(),17*3600)
        self.assertEqual(hours(date(2026,11,18)),(9,17))
    def test_evening_primary_backup_and_wrong_old_clock(self):
        """Verify evening primary backup and wrong old clock."""
        now=datetime(2026,11,4,17,tzinfo=timezone.utc)
        expected=due_for(date(2026,11,5))
        self.assertEqual(slot_for(now,'schedule','0 17 * * *',now=now),expected)
        self.assertEqual(slot_for(now.replace(minute=17),'schedule','17 17 * * *',now=now),expected)
        self.assertIsNone(slot_for(now,'schedule','0 7 * * *',now=now))
    def test_noon_expiry_never_rolls_over(self):
        """Verify noon expiry never rolls over."""
        created=datetime(2026,11,4,17,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,'expired'):
            slot_for(created,'workflow_dispatch',now=datetime(2026,11,5,10,tzinfo=timezone.utc))
    def test_evening_provenance_and_report_target(self):
        """Verify evening provenance and report target."""
        created='2026-11-04T17:00:10Z';day=date(2026,11,5)
        run={'status':'completed','conclusion':'success','event':'schedule','created_at':created}
        decision={'due_at':due_for(day).isoformat(),'reason':'eligible'}
        self.assertEqual(clock_source(run,decision,day),'github-schedule')
        run['created_at']='2026-11-05T07:00:00Z'
        self.assertIsNone(clock_source(run,decision,day))
        self.assertEqual(audit_day(datetime.fromisoformat(created).astimezone(production_at(day).tzinfo)),day)
    def test_baseline_dst_is_preserved(self):
        """Verify baseline dst is preserved."""
        self.assertEqual(due_for(date(2030,1,3)).hour,15)
        self.assertEqual(due_for(date(2030,7,3)).hour,14)

    def test_manual_trial_run_needs_explicit_date_outside_evening(self):
        """An accidental morning manual dispatch cannot start tomorrow's production."""
        now=datetime(2026,11,5,7,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,'Explicit publication date'):
            slot_for(now,'workflow_dispatch',now=now)
