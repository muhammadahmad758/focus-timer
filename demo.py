"""Headless demo — no window needed.

Simulates a week of focus sessions in a temporary log, prints the
dashboard numbers, and generates the two PNG charts. Run:

    py demo.py
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from focus_timer import charts, stats
from focus_timer.storage import SessionLog
from focus_timer.timer_core import PomodoroTimer


def main():
    print("== Timer core demo ==")
    timer = PomodoroTimer(focus_minutes=1, break_minutes=1)
    timer.start()
    for _ in range(60):
        event = timer.tick()
    print(f"After 60 ticks of a 1-minute focus: event={event}, "
          f"mode={timer.mode}, completed={timer.completed_focus_sessions}")
    assert event == "focus_completed" and timer.mode == "break"

    print("\n== Simulated week ==")
    with tempfile.TemporaryDirectory() as tmp:
        log = SessionLog(Path(tmp) / "sessions.json")
        today = datetime.now()
        plan = {0: 3, 1: 2, 2: 4, 3: 1, 5: 2, 6: 3}  # days ago -> sessions (day 4 missed)
        for days_ago, count in sorted(plan.items()):
            when = today - timedelta(days=days_ago)
            for _ in range(count):
                log.add_session(25, when=when)
        s = stats.summary(log)
        print(f"Today: {s['today_sessions']} sessions, {s['today_minutes']} min")
        print(f"Streak: {s['streak']} day(s)  (note the missed day in the plan)")
        print(f"Total: {s['total_sessions']} sessions, {s['total_minutes']} min")
        print(f"Best day: {s['best_day']} with {s['best_day_minutes']} min")
        print("\nDaily (last 7 days):")
        for day, minutes, sessions in stats.daily_totals(log):
            print(f"  {day.strftime('%a %d %b')}: {minutes:>3} min ({sessions} sessions)")
        print("Weekly (last 4 weeks):")
        for start, minutes, sessions in stats.weekly_totals(log):
            print(f"  Week of {start.strftime('%d %b')}: {minutes:>3} min ({sessions} sessions)")
        out_dir = Path(__file__).resolve().parent / "charts"
        daily, weekly = charts.make_charts(log, out_dir)
        print(f"\nCharts written: {daily.name}, {weekly.name} in {out_dir}")


if __name__ == "__main__":
    main()
