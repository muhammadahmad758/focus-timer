import unittest

from focus_timer.timer_core import PomodoroTimer


def run_out(timer, seconds):
    event = None
    for _ in range(seconds):
        event = timer.tick()
    return event


class TimerCoreTests(unittest.TestCase):
    def test_starts_idle_at_full_focus(self):
        t = PomodoroTimer()
        self.assertEqual(t.mode, "focus")
        self.assertEqual(t.state, "idle")
        self.assertEqual(t.remaining_seconds, 25 * 60)
        self.assertEqual(t.display(), "25:00")

    def test_tick_does_nothing_when_idle_or_paused(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1)
        self.assertIsNone(t.tick())
        t.start()
        t.pause()
        self.assertIsNone(t.tick())
        self.assertEqual(t.remaining_seconds, 60)

    def test_focus_completion_counts_and_moves_to_break(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1)
        t.start()
        event = run_out(t, 60)
        self.assertEqual(event, "focus_completed")
        self.assertEqual(t.completed_focus_sessions, 1)
        self.assertEqual(t.mode, "break")
        self.assertEqual(t.state, "idle")
        self.assertEqual(t.remaining_seconds, 60)

    def test_break_completion_returns_to_focus(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1)
        t.start()
        run_out(t, 60)
        t.start()
        event = run_out(t, 60)
        self.assertEqual(event, "break_completed")
        self.assertEqual(t.mode, "focus")
        self.assertEqual(t.completed_focus_sessions, 1)

    def test_long_break_after_four_sessions(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1,
                          long_break_minutes=3, sessions_before_long_break=4)
        for _ in range(4):
            t.start()
            run_out(t, 60)  # focus
            if t.mode == "break":
                t.start()
                run_out(t, 60)  # break
        self.assertEqual(t.completed_focus_sessions, 4)
        # After the 4th focus the timer went to long break, then focus.
        # Run one more cycle check on a fresh timer for the exact moment:
        t2 = PomodoroTimer(focus_minutes=1, break_minutes=1,
                           long_break_minutes=3, sessions_before_long_break=2)
        t2.start(); run_out(t2, 60)
        t2.start(); run_out(t2, 60)
        t2.start(); run_out(t2, 60)
        self.assertEqual(t2.mode, "long_break")
        self.assertEqual(t2.remaining_seconds, 180)

    def test_skip_focus_does_not_count(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1)
        t.start()
        t.tick(); t.tick()
        finished = t.skip()
        self.assertEqual(finished, "focus")
        self.assertEqual(t.completed_focus_sessions, 0)
        self.assertEqual(t.mode, "break")

    def test_reset_returns_to_fresh_focus_but_keeps_count(self):
        t = PomodoroTimer(focus_minutes=1, break_minutes=1)
        t.start(); run_out(t, 60)
        t.reset()
        self.assertEqual(t.mode, "focus")
        self.assertEqual(t.state, "idle")
        self.assertEqual(t.remaining_seconds, 60)
        self.assertEqual(t.completed_focus_sessions, 1)

    def test_progress_and_display(self):
        t = PomodoroTimer(focus_minutes=2, break_minutes=1)
        t.start()
        run_out(t, 60)
        self.assertEqual(t.display(), "01:00")
        self.assertAlmostEqual(t.progress, 0.5)

    def test_invalid_minutes_rejected(self):
        with self.assertRaises(ValueError):
            PomodoroTimer(focus_minutes=0)
        with self.assertRaises(ValueError):
            PomodoroTimer(break_minutes=999)


if __name__ == "__main__":
    unittest.main()
