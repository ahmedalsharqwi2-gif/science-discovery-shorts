import unittest
from datetime import date
from scripts.publication_slots import stock_matrix


class PublicationSlotsTests(unittest.TestCase):
    def matrix(self, dates="", hours=""):
        return stock_matrix(dates, hours, today=date(2026, 10, 12))["include"]

    def test_empty_preserves_existing_default_schedule(self):
        self.assertEqual(self.matrix(), [{"date": "", "hour": ""}])

    def test_single_iso_slot(self):
        self.assertEqual(self.matrix("2026-10-13", "12"), [{"date": "2026-10-13", "hour": "12"}])

    def test_observed_failed_input_expands_to_six_distinct_episodes(self):
        rows = self.matrix("13,14,15-10-2026", "12,18")
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[0], {"date": "2026-10-13", "hour": "12"})
        self.assertEqual(rows[-1], {"date": "2026-10-15", "hour": "18"})

    def test_arabic_digits_and_separators(self):
        self.assertEqual(self.matrix("١٣،١٤،١٥-١٠-٢٠٢٦", "١٢،١٨"), self.matrix("13,14,15-10-2026", "12,18"))

    def test_deduplicates_iso_days_and_hours(self):
        self.assertEqual(self.matrix("2026-10-14,2026-10-13,2026-10-13", "18,12,12"), self.matrix("13,14-10-2026", "12,18"))

    def test_invalid_calendar_dates_are_rejected(self):
        for dates in ("31-02-2026", "garbage", "13,14-13-2026"):
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                self.matrix(dates, "12")

    def test_requires_complete_input_and_allowed_hours(self):
        for dates, hours in (("", "12"), ("2026-10-13", ""), ("2026-10-13", "13"), ("2026-10-13", "12,")):
            with self.subTest(hours=hours), self.assertRaises(ValueError):
                self.matrix(dates, hours)

    def test_past_and_excessively_future_dates_are_rejected(self):
        for dates in ("2026-10-11", "2026-10-17", "13,20-10-2026"):
            with self.subTest(dates=dates), self.assertRaises(ValueError):
                self.matrix(dates, "18")


if __name__ == "__main__":
    unittest.main()
