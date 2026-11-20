"""The Pomodoro timer state machine — pure logic, no GUI imports.

The GUI calls ``tick()`` once per second. Everything here can be unit
tested without a window, a clock, or real waiting: tests just call
``tick()`` as many times as they want.

Modes: "focus", "break", "long_break".
States: "idle" (ready, not started), "running", "paused".
"""

from . import config

FOCUS = "focus"
BREAK = "break"
LONG_BREAK = "long_break"


class PomodoroTimer:
    def __init__(
        self,
        focus_minutes=config.DEFAULT_FOCUS_MINUTES,
        break_minutes=config.DEFAULT_BREAK_MINUTES,
        long_break_minutes=config.DEFAULT_LONG_BREAK_MINUTES,
        sessions_before_long_break=config.SESSIONS_BEFORE_LONG_BREAK,
    ):
        for name, value in (
            ("focus_minutes", focus_minutes),
            ("break_minutes", break_minutes),
            ("long_break_minutes", long_break_minutes),
        ):
            if not (config.MIN_MINUTES <= int(value) <= config.MAX_MINUTES):
                raise ValueError(
                    f"{name} must be between {config.MIN_MINUTES} and "
                    f"{config.MAX_MINUTES} minutes, got {value!r}"
                )
        if int(sessions_before_long_break) < 1:
            raise ValueError("sessions_before_long_break must be at least 1")

        self.focus_seconds = int(focus_minutes) * 60
        self.break_seconds = int(break_minutes) * 60
        self.long_break_seconds = int(long_break_minutes) * 60
        self.sessions_before_long_break = int(sessions_before_long_break)

        self.mode = FOCUS
        self.state = "idle"
        self.remaining_seconds = self.focus_seconds
        self.completed_focus_sessions = 0
        # Seconds of focus actually elapsed in the current focus session.
        self.focus_elapsed_seconds = 0

    # -- controls ---------------------------------------------------------

    def start(self):
        if self.state != "running":
            self.state = "running"

    def pause(self):
        if self.state == "running":
            self.state = "paused"

    def toggle(self):
        if self.state == "running":
            self.pause()
        else:
            self.start()

    def reset(self):
        """Back to a fresh, idle focus session. Completed count is kept."""
        self.mode = FOCUS
        self.state = "idle"
        self.remaining_seconds = self.focus_seconds
        self.focus_elapsed_seconds = 0

    def skip(self):
        """End the current mode early and move to the next one (idle).

        Returns the finished mode. A skipped focus session does NOT count
        as completed — only a focus session that runs to zero counts.
        """
        finished = self.mode
        self._advance(count_focus=False)
        return finished

    # -- the clock --------------------------------------------------------

    def tick(self, seconds=1):
        """Advance the timer. Returns an event name or None.

        Events: "focus_completed", "break_completed", "long_break_completed".
        Does nothing unless the timer is running.
        """
        if self.state != "running" or seconds <= 0:
            return None
        step = int(seconds)
        if self.mode == FOCUS:
            self.focus_elapsed_seconds += min(step, self.remaining_seconds)
        self.remaining_seconds -= step
        if self.remaining_seconds > 0:
            return None
        self.remaining_seconds = 0
        finished = self.mode
        self._advance(count_focus=(finished == FOCUS))
        if finished == FOCUS:
            return "focus_completed"
        return f"{finished}_completed"

    def _advance(self, count_focus):
        if self.mode == FOCUS:
            if count_focus:
                self.completed_focus_sessions += 1
            if (
                count_focus
                and self.completed_focus_sessions > 0
                and self.completed_focus_sessions % self.sessions_before_long_break == 0
            ):
                self.mode = LONG_BREAK
                self.remaining_seconds = self.long_break_seconds
            else:
                self.mode = BREAK
                self.remaining_seconds = self.break_seconds
        else:
            self.mode = FOCUS
            self.remaining_seconds = self.focus_seconds
        self.state = "idle"
        self.focus_elapsed_seconds = 0

    # -- display helpers ----------------------------------------------------

    @property
    def total_seconds_for_mode(self):
        if self.mode == FOCUS:
            return self.focus_seconds
        if self.mode == BREAK:
            return self.break_seconds
        return self.long_break_seconds

    @property
    def progress(self):
        """0.0 at the start of a mode, 1.0 when it finishes."""
        total = self.total_seconds_for_mode
        if total <= 0:
            return 0.0
        return min(1.0, max(0.0, 1.0 - self.remaining_seconds / total))

    def display(self):
        minutes, seconds = divmod(max(0, self.remaining_seconds), 60)
        return f"{minutes:02d}:{seconds:02d}"

    def mode_label(self):
        return {
            FOCUS: "FOCUS",
            BREAK: "BREAK",
            LONG_BREAK: "LONG BREAK",
        }[self.mode]
