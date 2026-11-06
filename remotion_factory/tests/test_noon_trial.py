import unittest
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from remotion_factory.schedule import hours, due_for, production_at, checkpoints

CAIRO = ZoneInfo("Africa/Cairo")

class PermanentNoonSchedule(unittest.TestCase):
    def test_permanent_hours_and_post_window_date(self):
        for day in (date(2026, 11, 3), date(2026, 11, 18), date(2027, 3, 1)):
            self.assertEqual(hours(day), (19, 12))
            self.assertEqual(production_at(day).hour, 19)
            self.assertEqual(production_at(day).date(), day.replace(day=day.day) if False else day.fromordinal(day.toordinal()-1))

    def test_winter_and_summer_publication_utc(self):
        self.assertEqual(due_for(date(2026, 12, 15)), datetime(2026, 12, 15, 10, tzinfo=timezone.utc))
        self.assertEqual(due_for(date(2027, 7, 15)), datetime(2027, 7, 15, 9, tzinfo=timezone.utc))

    def test_production_is_previous_cairo_day(self):
        for day in (date(2026, 12, 15), date(2027, 7, 15)):
            p = production_at(day)
            self.assertEqual(p.tzinfo, CAIRO)
            self.assertEqual(p.hour, 19)
            self.assertEqual(p.date().toordinal(), day.toordinal()-1)

    def test_noon_checkpoints_are_permanent(self):
        self.assertEqual(checkpoints(date(2027, 3, 1)), ((9,30),(11,15),(12,30),(21,30)))

if __name__ == "__main__":
    unittest.main()
