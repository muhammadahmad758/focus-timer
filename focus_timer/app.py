"""The tkinter GUI — a dark, violet Pomodoro window.

All timing logic lives in timer_core.py and all numbers in stats.py;
this file only draws the window and forwards button presses.
"""

import tkinter as tk
from tkinter import messagebox

from . import charts, config, stats
from .storage import SessionLog
from .timer_core import BREAK, FOCUS, LONG_BREAK, PomodoroTimer

BG = "#17141F"
PANEL = "#221E33"
TEXT = "#F3F0FF"
MUTED = "#A79FC0"
ACCENT = "#7C3AED"
ACCENT_LIGHT = "#A78BFA"
GREEN = "#34D399"
TEAL = "#2DD4BF"

MODE_COLORS = {FOCUS: ACCENT_LIGHT, BREAK: GREEN, LONG_BREAK: TEAL}
FONT = "Segoe UI"


def _beep(root):
    try:
        import winsound

        winsound.Beep(880, 250)
        winsound.Beep(1174, 400)
    except Exception:
        try:
            root.bell()
        except Exception:
            pass


class FocusTimerApp:
    def __init__(self, root, log=None):
        self.root = root
        self.log = log if log is not None else SessionLog()
        self.timer = PomodoroTimer()
        self._after_id = None

        root.title("Focus Timer & Productivity Dashboard")
        root.configure(bg=BG)
        root.geometry("500x640")
        root.minsize(460, 600)

        tk.Label(root, text="FOCUS TIMER", font=(FONT, 11, "bold"),
                 fg=MUTED, bg=BG).pack(pady=(22, 0))

        self.mode_label = tk.Label(root, text="FOCUS", font=(FONT, 20, "bold"),
                                   fg=ACCENT_LIGHT, bg=BG)
        self.mode_label.pack(pady=(6, 0))

        self.time_label = tk.Label(root, text="25:00", font=(FONT, 68, "bold"),
                                   fg=TEXT, bg=BG)
        self.time_label.pack(pady=(0, 4))

        self.progress = tk.Canvas(root, width=400, height=14, bg=BG,
                                  highlightthickness=0)
        self.progress.pack(pady=(4, 14))
        self.progress.create_rectangle(0, 2, 400, 12, fill=PANEL, outline="")
        self._progress_fill = self.progress.create_rectangle(
            0, 2, 0, 12, fill=ACCENT, outline="")

        buttons = tk.Frame(root, bg=BG)
        buttons.pack(pady=4)
        self.start_button = self._button(buttons, "Start", self._toggle,
                                         bg=ACCENT, width=10)
        self.start_button.pack(side="left", padx=6)
        self._button(buttons, "Reset", self._reset, bg=PANEL, width=10).pack(
            side="left", padx=6)
        self._button(buttons, "Skip", self._skip, bg=PANEL, width=10).pack(
            side="left", padx=6)

        self.status_label = tk.Label(root, text="Ready when you are.",
                                     font=(FONT, 11), fg=MUTED, bg=BG)
        self.status_label.pack(pady=(10, 0))

        settings = tk.Frame(root, bg=PANEL)
        settings.pack(pady=(18, 0), padx=28, fill="x")
        inner = tk.Frame(settings, bg=PANEL)
        inner.pack(pady=10)
        tk.Label(inner, text="Focus", font=(FONT, 10), fg=MUTED,
                 bg=PANEL).pack(side="left")
        self.focus_var = tk.StringVar(value=str(config.DEFAULT_FOCUS_MINUTES))
        tk.Spinbox(inner, from_=config.MIN_MINUTES, to=config.MAX_MINUTES,
                   width=4, textvariable=self.focus_var, font=(FONT, 11),
                   bg=BG, fg=TEXT, buttonbackground=PANEL,
                   insertbackground=TEXT, relief="flat").pack(side="left", padx=(4, 14))
        tk.Label(inner, text="Break", font=(FONT, 10), fg=MUTED,
                 bg=PANEL).pack(side="left")
        self.break_var = tk.StringVar(value=str(config.DEFAULT_BREAK_MINUTES))
        tk.Spinbox(inner, from_=config.MIN_MINUTES, to=config.MAX_MINUTES,
                   width=4, textvariable=self.break_var, font=(FONT, 11),
                   bg=BG, fg=TEXT, buttonbackground=PANEL,
                   insertbackground=TEXT, relief="flat").pack(side="left", padx=(4, 14))
        self._button(inner, "Apply", self._apply_settings, bg=ACCENT,
                     width=7).pack(side="left")

        self.stats_label = tk.Label(root, text="", font=(FONT, 12),
                                    fg=TEXT, bg=BG, justify="center")
        self.stats_label.pack(pady=(20, 0))

        self._button(root, "Open Dashboard", self._open_dashboard,
                     bg=PANEL, width=18).pack(pady=(16, 0))

        self._refresh()

    # -- helpers ------------------------------------------------------------

    def _button(self, parent, text, command, bg, width):
        return tk.Button(parent, text=text, command=command, width=width,
                         font=(FONT, 12, "bold"), bg=bg, fg="white",
                         activebackground=ACCENT_LIGHT, activeforeground="white",
                         relief="flat", cursor="hand2", pady=6)

    def _refresh(self):
        t = self.timer
        self.mode_label.config(text=t.mode_label(),
                               fg=MODE_COLORS[t.mode])
        self.time_label.config(text=t.display())
        self.progress.itemconfig(self._progress_fill, fill=MODE_COLORS[t.mode])
        self.progress.coords(self._progress_fill, 0, 2, 400 * t.progress, 12)
        self.start_button.config(
            text="Pause" if t.state == "running" else
            "Resume" if t.state == "paused" else "Start")
        s = stats.summary(self.log)
        self.stats_label.config(
            text=(f"Today: {s['today_sessions']} sessions  •  "
                  f"{s['today_minutes']} min\n"
                  f"Streak: {s['streak']} day(s)  •  "
                  f"Total: {s['total_minutes']} min in "
                  f"{s['total_sessions']} sessions"))

    # -- actions --------------------------------------------------------------

    def _toggle(self):
        self.timer.toggle()
        if self.timer.state == "running":
            self.status_label.config(text="Focusing..." if self.timer.mode == FOCUS
                                     else "On a break.")
            self._schedule_tick()
        else:
            self.status_label.config(text="Paused.")
            self._cancel_tick()
        self._refresh()

    def _reset(self):
        self._cancel_tick()
        self.timer.reset()
        self.status_label.config(text="Reset. Ready when you are.")
        self._refresh()

    def _skip(self):
        self._cancel_tick()
        finished = self.timer.skip()
        if finished == FOCUS:
            self.status_label.config(
                text="Focus skipped — not counted. Break is ready.")
        else:
            self.status_label.config(text="Break skipped. Focus is ready.")
        self._refresh()

    def _apply_settings(self):
        try:
            focus = int(self.focus_var.get())
            brk = int(self.break_var.get())
            self.timer = PomodoroTimer(focus_minutes=focus, break_minutes=brk)
        except (ValueError, TypeError):
            messagebox.showerror(
                "Settings",
                f"Minutes must be whole numbers between "
                f"{config.MIN_MINUTES} and {config.MAX_MINUTES}.")
            return
        self._cancel_tick()
        self.status_label.config(
            text=f"Settings applied: {focus} min focus, {brk} min break.")
        self._refresh()

    # -- ticking ----------------------------------------------------------------

    def _schedule_tick(self):
        self._cancel_tick()
        self._after_id = self.root.after(1000, self._tick)

    def _cancel_tick(self):
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self):
        self._after_id = None
        event = self.timer.tick()
        if event == "focus_completed":
            minutes = self.timer.focus_seconds // 60
            self.log.add_session(minutes)
            _beep(self.root)
            self.status_label.config(
                text=f"Focus session saved: +{minutes} min. Take your break.")
        elif event in ("break_completed", "long_break_completed"):
            _beep(self.root)
            self.status_label.config(text="Break over. Ready to focus again?")
        self._refresh()
        if self.timer.state == "running":
            self._schedule_tick()

    # -- dashboard ----------------------------------------------------------------

    def _open_dashboard(self):
        win = tk.Toplevel(self.root)
        win.title("Productivity Dashboard")
        win.configure(bg=BG)
        win.geometry("520x560")

        tk.Label(win, text="LAST 7 DAYS", font=(FONT, 12, "bold"),
                 fg=MUTED, bg=BG).pack(pady=(18, 6))
        self._bar_rows(win, [
            (d.strftime("%a %d %b"), m) for d, m, _ in stats.daily_totals(self.log)
        ])

        tk.Label(win, text="LAST 4 WEEKS (from Monday)", font=(FONT, 12, "bold"),
                 fg=MUTED, bg=BG).pack(pady=(18, 6))
        self._bar_rows(win, [
            (f"Week of {d.strftime('%d %b')}", m)
            for d, m, _ in stats.weekly_totals(self.log)
        ])

        s = stats.summary(self.log)
        best = s["best_day"] or "—"
        tk.Label(win, text=(f"Streak: {s['streak']} day(s)   •   "
                            f"Best day: {best} ({s['best_day_minutes']} min)"),
                 font=(FONT, 12), fg=TEXT, bg=BG).pack(pady=(18, 0))

        def save_charts():
            from pathlib import Path

            out_dir = Path(__file__).resolve().parent.parent / "charts"
            daily, weekly = charts.make_charts(self.log, out_dir)
            messagebox.showinfo(
                "Charts saved",
                f"Saved:\n{daily}\n{weekly}", parent=win)

        self._button(win, "Save charts as PNG", save_charts, bg=ACCENT,
                     width=20).pack(pady=(16, 0))

    def _bar_rows(self, parent, rows):
        max_minutes = max([m for _, m in rows] + [1])
        for label, minutes in rows:
            row = tk.Frame(parent, bg=BG)
            row.pack(fill="x", padx=24, pady=2)
            tk.Label(row, text=label, font=(FONT, 10), fg=TEXT, bg=BG,
                     width=18, anchor="w").pack(side="left")
            canvas = tk.Canvas(row, width=200, height=12, bg=BG,
                               highlightthickness=0)
            canvas.pack(side="left", padx=6)
            canvas.create_rectangle(0, 1, 200, 11, fill=PANEL, outline="")
            canvas.create_rectangle(0, 1, 200 * minutes / max_minutes, 11,
                                    fill=ACCENT, outline="")
            tk.Label(row, text=f"{minutes} min", font=(FONT, 10), fg=MUTED,
                     bg=BG).pack(side="left")


def main():
    root = tk.Tk()
    FocusTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
