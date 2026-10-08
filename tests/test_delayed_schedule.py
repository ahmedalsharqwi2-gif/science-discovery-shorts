import os
import re
import tempfile
import textwrap
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


class DelayedScheduleTests(unittest.TestCase):
    def slot(self, date, expression):
        root = Path(__file__).resolve().parents[1]
        workflow = root / '.github/workflows/auto_publish.yml'
        if not workflow.exists():
            workflow = root / '.github/workflows/main.yml'
        match = re.search(r"python - <<'PY'\n(.*?)\n          PY", workflow.read_text(), re.S)
        self.assertIsNotNone(match)
        code = textwrap.dedent(match.group(1))
        now = datetime.fromisoformat(date).astimezone(timezone.utc)
        class FrozenDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now.astimezone(tz) if tz else now.replace(tzinfo=None)
        with tempfile.TemporaryDirectory() as directory:
            envfile = Path(directory) / 'env'
            with patch('datetime.datetime', FrozenDateTime), patch.dict(os.environ, {'SCHEDULE_EXPR': expression, 'PUBLISH_NOW': 'false', 'GITHUB_ENV': str(envfile)}):
                exec(compile(code, 'publication slot', 'exec'), {})
            return envfile.read_text().strip().split('=', 1)[1]

    def test_delayed_morning_reaches_today_evening(self):
        self.assertEqual(self.slot('2026-10-08T13:06:00+00:00', '17 6 * * *'), '2026-10-08T15:00:00Z')

    def test_normal_morning_keeps_noon(self):
        self.assertEqual(self.slot('2026-10-08T06:17:00+00:00', '17 6 * * *'), '2026-10-08T09:00:00Z')

    def test_evening_respects_cairo_winter_offset(self):
        self.assertEqual(self.slot('2026-11-08T12:17:00+00:00', '17 12 * * *'), '2026-11-08T16:00:00Z')


if __name__ == '__main__':
    unittest.main()
