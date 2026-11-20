"""GUI smoke tests — skipped automatically when no display exists.

On a machine with a display (or Xvfb) these build the real v2.0 window,
switch all three views, start/pause the timer, apply new durations and
resize the window. They never touch the real session log: a temporary
log and settings file are injected.
"""

import tempfile
import unittest
from pathlib import Path


class GuiSmokeTests(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk

            self.root = tk.Tk()
        except Exception:
            self.skipTest("no display available")
        self.root.withdraw()
        tmp = tempfile.mkdtemp()
        from focus_timer.app import FocusTimerApp
        from focus_timer.settings import AppSettings
        from focus_timer.storage import SessionLog

        settings = AppSettings(Path(tmp) / "settings.json")
        settings.set("animations_enabled", False)
        settings.set("sound_enabled", False)
        self.app = FocusTimerApp(
            self.root,
            log=SessionLog(Path(tmp) / "sessions.json"),
            settings=settings,
        )
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_all_three_views_switch(self):
        for view in ("dashboard", "settings", "timer"):
            self.app._show_view(view)
            self.root.update()
            self.assertEqual(self.app._current_view, view)

    def test_start_pause_and_skip(self):
        self.app._show_view("timer")
        self.app._toggle()
        self.root.update()
        self.assertEqual(self.app.timer.state, "running")
        event = None
        for _ in range(3):
            event = self.app.timer.tick()
        self.app._toggle()
        self.assertEqual(self.app.timer.state, "paused")
        finished = self.app.timer.skip()
        self.assertEqual(finished, "focus")

    def test_apply_durations_from_settings_view(self):
        self.app._show_view("settings")
        self.app.duration_vars["focus_minutes"].set("30")
        self.app.duration_vars["break_minutes"].set("10")
        self.app.duration_vars["long_break_minutes"].set("20")
        self.app._apply_durations()
        self.root.update()
        self.assertEqual(self.app.timer.focus_seconds, 30 * 60)
        self.assertEqual(self.app.settings.get("focus_minutes"), 30)

    def test_resize_keeps_app_alive(self):
        self.root.geometry("1200x800")
        self.root.update_idletasks()
        self.root.update()
        self.root.geometry("940x620")
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(self.app.timer.display(), "25:00")


if __name__ == "__main__":
    unittest.main()
