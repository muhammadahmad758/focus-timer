import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from focus_timer import stats
from focus_timer.storage import SessionLog


def make_log(tmp, plan):
    """plan: {days_ago: [minutes, ...]} relative to a fixed today."""
    log = SessionLog(Path(tmp) / "sessions.json")
    today = date(2026, 11, 20)  # a Friday
    for days_ago, minutes_list in plan.items():
        when = datetime.combine(today - timedelta(days=days_ago),
                                datetime.min.time())
        for minutes in minutes_list:
            log.add_session(minutes, when=when)
    return log, today


class StorageTests(unittest.TestCase):
    def test_add_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, _ = make_log(tmp, {0: [25, 25]})
            self.assertEqual(log.total_sessions(), 2)
            self.assertEqual(log.total_minutes(), 50)
            again = SessionLog(Path(tmp) / "sessions.json")
            self.assertEqual(again.total_sessions(), 2)
            self.assertEqual(again.minutes_on(date(2026, 11, 20)), 50)

    def test_corrupt_file_never_crashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.json"
            path.write_text("{ not json !!", encoding="utf-8")
            log = SessionLog(path)
            self.assertEqual(log.total_sessions(), 0)
            log.add_session(25)
            self.assertEqual(SessionLog(path).total_sessions(), 1)

    def test_bad_records_are_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sessions.json"
            path.write_text(json.dumps([
                {"date": "2026-11-20", "minutes": 25},
                {"nope": True},
                {"date": "2026-11-20", "minutes": "abc"},
            ]), encoding="utf-8")
            log = SessionLog(path)
            self.assertEqual(log.total_sessions(), 1)


class StatsTests(unittest.TestCase):
    def test_daily_totals_last_7_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, today = make_log(tmp, {0: [25], 6: [50], 7: [99]})
            rows = stats.daily_totals(log, days=7, today=today)
            self.assertEqual(len(rows), 7)
            self.assertEqual(rows[-1][1], 25)   # today
            self.assertEqual(rows[0][1], 50)    # 6 days ago
            self.assertNotIn(99, [m for _, m, _ in rows])  # 7 days ago excluded

    def test_streak_counts_back_from_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, today = make_log(tmp, {0: [25], 1: [25], 2: [25], 4: [25]})
            self.assertEqual(stats.current_streak(log, today=today), 3)

    def test_streak_survives_no_session_yet_today(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, today = make_log(tmp, {1: [25], 2: [25]})
            self.assertEqual(stats.current_streak(log, today=today), 2)

    def test_streak_zero_when_yesterday_missed(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, today = make_log(tmp, {2: [25], 3: [25]})
            self.assertEqual(stats.current_streak(log, today=today), 0)

    def test_weekly_totals_group_by_monday(self):
        with tempfile.TemporaryDirectory() as tmp:
            # 2026-11-20 is a Friday; its week starts Mon 2026-11-16.
            log, today = make_log(tmp, {0: [25], 4: [25], 7: [50]})
            rows = stats.weekly_totals(log, weeks=2, today=today)
            self.assertEqual(rows[-1][0], date(2026, 11, 16))
            self.assertEqual(rows[-1][1], 50)   # Fri + Mon of this week
            self.assertEqual(rows[0][1], 50)    # last week's session

    def test_summary_and_best_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            log, today = make_log(tmp, {0: [25, 25], 1: [25]})
            s = stats.summary(log, today=today)
            self.assertEqual(s["today_minutes"], 50)
            self.assertEqual(s["today_sessions"], 2)
            self.assertEqual(s["total_minutes"], 75)
            self.assertEqual(s["best_day"], "2026-11-20")
            self.assertEqual(s["best_day_minutes"], 50)


if __name__ == "__main__":
    unittest.main()
