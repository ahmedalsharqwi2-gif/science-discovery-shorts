import unittest
from datetime import datetime, timedelta
from scripts.replenish_stock import desired_slots, next_missing_slot


class RollingReserveTests(unittest.TestCase):
    now = datetime.fromisoformat("2026-10-12T21:00:00+03:00")

    def test_evening_reserve_contains_next_four_days_and_no_missed_today(self):
        slots = list(desired_slots(self.now))
        self.assertEqual(len(slots), 8)
        self.assertEqual(slots[0][1], "stock 2026-10-13 12 Cairo")
        self.assertEqual(slots[-1][1], "stock 2026-10-16 18 Cairo")

    def test_active_production_prevents_pending_run_eviction(self):
        self.assertIsNone(next_missing_slot([{"status": "in_progress"}], self.now))

    def test_success_skips_only_its_exact_slot(self):
        selected = next_missing_slot([{"display_title": "stock 2026-10-13 12 Cairo", "conclusion": "success"}], self.now)
        self.assertEqual(selected[1], "stock 2026-10-13 18 Cairo")

    def test_recent_failure_cools_down_while_other_slots_can_fill(self):
        runs = [{"display_title": "stock 2026-10-13 12 Cairo", "conclusion": "failure", "updated_at": self.now.isoformat()}]
        self.assertEqual(next_missing_slot(runs, self.now)[1], "stock 2026-10-13 18 Cairo")

    def test_four_failed_attempts_are_retried_after_cooldown(self):
        runs = [{"display_title": "stock 2026-10-13 12 Cairo", "conclusion": "failure", "updated_at": (self.now - timedelta(hours=3)).isoformat()}] * 4
        self.assertEqual(next_missing_slot(runs, self.now)[1], "stock 2026-10-13 12 Cairo")


if __name__ == "__main__":
    unittest.main()
