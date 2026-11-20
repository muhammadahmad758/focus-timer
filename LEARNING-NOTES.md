# Learning Notes — Focus Timer & Productivity Dashboard

The concepts in this project, in the order you meet them in the code.

## 1. Separate the brain from the window

`timer_core.py` never imports tkinter. The timer is a **state machine**:

- modes: `focus`, `break`, `long_break`
- states: `idle`, `running`, `paused`
- one method, `tick()`, moves time forward and reports an *event*
  (`focus_completed`, …) when a mode finishes.

Because the brain has no GUI, tests can simulate a whole Pomodoro by
calling `tick()` 1,500 times in a loop — no waiting 25 real minutes.
This is the same trick as Flappy Bird AI's `game_core.py`. Whenever you
build a GUI app, ask: "what is the pure-logic core I can test without
the window?"

## 2. Events, not side effects

`tick()` doesn't save anything or beep — it *returns* what happened,
and the GUI decides what to do (log the session, play a sound, update
the label). The core stays reusable: a command-line version could use
the same class and just print the events (see `demo.py`).

## 3. Streak logic is a definition, not a formula

"Streak" sounds simple until you define it:

- A day counts if it has **≥ 1 completed session**.
- The streak can end **today** (already logged) or **yesterday**
  (today not logged *yet* — the day isn't over, so the streak is
  still alive).
- It breaks only after a **full missed day**.

`stats.current_streak()` walks backwards day by day from that anchor.
All three cases (ends today / ends yesterday / broken) have their own
test. Most "simple" features hide a definition like this — write the
definition down first, then code it.

## 4. Weeks need an anchor

Weekly totals group by **Monday** (`today - timedelta(days=today.weekday())`),
not by "last 7 days". That makes weeks comparable: this week vs last
week always means Monday–Sunday blocks.

## 5. Defensive storage

`storage.py` writes atomically (write a `.tmp` file, then
`os.replace()`), so a crash mid-save can't corrupt your history. On
load, anything that isn't a proper record is dropped instead of
crashing. Your data file *will* eventually get corrupted by something —
plan for it.

## 6. GUI timing with `after()`

tkinter has no threads in this app. The GUI schedules itself:
`root.after(1000, self._tick)` — "call me again in one second". Each
tick updates the clock, the progress bar, and reschedules only while
running. Pause = cancel the scheduled call. This cooperative loop is
how most simple GUI apps animate without freezing the window.
