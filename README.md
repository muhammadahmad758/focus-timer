# Focus Timer & Productivity Dashboard

An original desktop Pomodoro timer by **Muhammad Ahmad Farooq** — with
automatic session logging, a productivity dashboard, and a streak
counter. Built with Python, tkinter, and matplotlib. Free, offline,
no accounts, no API keys.

## What it does

- **Pomodoro timer** — 25 min focus / 5 min break by default, with a
  15 min long break after every 4 focus sessions. Durations are
  adjustable in the app (1–180 min).
- **Automatic logging** — every completed focus session is saved to
  `data/sessions.json` the moment it finishes. No buttons to remember.
- **Dashboard** — today's sessions and minutes, total focus time, best
  day, last 7 days and last 4 weeks as bars, plus exportable PNG charts.
- **Streak counter** — consecutive days with at least one completed
  session. The streak stays alive if today isn't logged *yet*; it only
  breaks after a full missed day.
- **Sound + status** — a beep and a status line when a session ends.
- Skipping a focus session does **not** count it — only finished
  sessions are logged. Honest numbers only.

## Run it

You need Python 3.10+ and matplotlib:

```
py -m pip install matplotlib
py main.py
```

(tkinter ships with Python on Windows — nothing else to install.)

Other entry points:

```
py -m focus_timer        same app, as a package
py demo.py               headless demo: simulated week + charts, no window
py -m unittest discover -s tests -v    run the test suite (18 tests)
```

## How it is built

| File | Job |
|---|---|
| `focus_timer/timer_core.py` | The Pomodoro state machine (focus → break → long break). Pure logic, no GUI — fully unit-tested. |
| `focus_timer/storage.py` | Session log in `data/sessions.json`. Atomic writes; a corrupt file never crashes the app. |
| `focus_timer/stats.py` | Daily/weekly totals, streak, best day — pure functions over the log. |
| `focus_timer/charts.py` | matplotlib PNG charts (`charts/daily_chart.png`, `charts/weekly_chart.png`). |
| `focus_timer/app.py` | The tkinter window (dark violet theme). Only draws and forwards clicks. |
| `focus_timer/config.py` | All defaults in one place. |

## Data

Your sessions live in `data/sessions.json`, one record per session:

```json
{"date": "2026-11-20", "minutes": 25, "ended_at": "15:30:05"}
```

Delete the file to start fresh. Nothing ever leaves your computer.

## Honest limits

- The timer counts GUI ticks (one per second); if the app is closed
  mid-session, that session is lost — it is not running in the
  background.
- Charts are generated on demand from the dashboard window, not live.
- The GUI was smoke-tested headlessly; the full click-through is best
  verified on your own PC.

## License

MIT — see `LICENSE`.
