# Focus Timer & Productivity Dashboard — v2.0 "Midnight Glass"

An original desktop Pomodoro timer by **Muhammad Ahmad Farooq**,
redesigned in v2.0 as a premium, futuristic productivity app:
glassmorphism panels, a dominant animated progress ring, ambient
midnight-blue/violet lighting, original sounds, and a three-view
interface (Timer / Dashboard / Settings). Python + tkinter +
matplotlib. Free, fully offline, no accounts, no API keys.

All v1.0 functionality is preserved — the timer logic, storage,
statistics and streak rules are byte-for-byte the same code. Only the
interface was rebuilt.

## What's new in v2.0

- **Midnight Glass design** — deep navy gradient background, simulated
  frosted-glass cards with hairline borders, electric blue + violet
  accents, restrained ambient glow behind the ring.
- **The ring is the hero** — a large circular progress indicator with a
  blue→violet gradient arc (teal for Short Break, soft violet for Long
  Break), elegant countdown typography, session dots for the 4-session
  cycle, and a gentle pulse when a session completes. The ring animates
  smoothly between seconds; the clock itself still ticks exactly once
  per second.
- **Three views, one window** — a slim navigation rail switches Timer,
  Dashboard and Settings. No pop-up windows.
- **Sounds, original and offline** — start / pause / focus-complete /
  break-complete chimes synthesized locally as WAV files (stdlib only).
  Settings has a sound on/off toggle, a volume slider and a test
  button. Volume works by rendering the chime at your chosen level —
  winsound itself has no volume control.
- **Settings that persist** — durations (focus / short break / long
  break), sound and animation preferences save automatically to
  `data/settings.json`. Session history is a separate file and is
  never touched by settings.
- **Animation controls** — turn all animations off, or just the slow
  ambient lighting drift, in Settings.
- **Dashboard restyled** — glass stat cards, rounded native bars for
  the last 7 days and last 4 weeks, and PNG chart exports in the new
  midnight theme.
- Press **Space** to start/pause from the Timer view.

## What it does (unchanged from v1.0)

- **Pomodoro timer** — 25 / 5 / 15 minutes by default, long break
  after every 4 focus sessions. Adjustable from 1–180 minutes.
- **Automatic logging** — every completed focus session is saved to
  `data/sessions.json` the moment it finishes. Skipped sessions do not
  count. Honest numbers only.
- **Streak counter** — consecutive days with at least one completed
  session; it stays alive until a full day is missed.

## Run it

```
py -m pip install matplotlib
py main.py
```

(tkinter ships with Python on Windows — nothing else to install.)

```
py demo.py                              headless demo + charts, no window
py -m unittest discover -s tests -v     29 tests (18 original + 11 new)
```

## How it is built

| File | Job |
|---|---|
| `focus_timer/timer_core.py` | The Pomodoro state machine. Pure logic, no GUI — **unchanged from v1.0**. |
| `focus_timer/storage.py` | Session log (`data/sessions.json`), atomic writes — **unchanged**. |
| `focus_timer/stats.py` | Daily/weekly totals, streak, best day — **unchanged**. |
| `focus_timer/charts.py` | matplotlib PNG charts, restyled to the midnight theme. |
| `focus_timer/app.py` | The v2.0 interface: gradient stage, ring, glass cards, three views, animation loops. |
| `focus_timer/ui_theme.py` | The Midnight Glass palette, fonts (Segoe UI Variable first) and colour helpers. |
| `focus_timer/settings.py` | Preferences in `data/settings.json`, validated, corrupt-proof. |
| `focus_timer/sounds.py` | Synthesizes and plays the original WAV chimes; volume rendering. |
| `assets/sounds/` | The four generated chime files. |

## An honest note on "glass"

Tkinter cannot blur your real desktop through the window. The glass
here is *simulated* — layered translucent-look panels over a gradient
with ambient glow, drawn inside the app. It looks like glass; it does
not blur what is behind the window.

## Honest limits

- The timer counts GUI ticks (one per second); closing the app
  mid-session loses that session — it does not run in the background.
- Sound playback uses Windows' winsound; on other systems the app
  falls back to a simple bell.
- v2.0 was built and verified running on a real (virtual) display with
  automated interaction tests; the final Windows click-through is best
  confirmed on your own PC.

## License

MIT — see `LICENSE`.
