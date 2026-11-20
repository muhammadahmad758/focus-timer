"""Focus Timer v2.0 — the Midnight Glass interface.

One window, three views (Timer / Dashboard / Settings), a dominant
circular progress ring, glass stat cards and restrained ambient motion.

All logic still lives outside this file: timer_core.py (the Pomodoro
state machine, ticking exactly once per second), storage.py (session
log), stats.py (numbers) and charts.py (PNG exports). The smooth ring
animation is visual interpolation only — it never touches the clock.
"""

import time
import tkinter as tk
from pathlib import Path

from . import charts, config, stats, ui_theme as theme
from .settings import AppSettings
from .sounds import SoundPlayer
from .storage import SessionLog
from .timer_core import BREAK, FOCUS, LONG_BREAK, PomodoroTimer

STAGE_BG = "#0B1120"
ERROR = "#F87171"
SEGMENTS = 180


class FocusTimerApp:
    def __init__(self, root, log=None, settings=None):
        self.root = root
        self.settings = settings if settings is not None else AppSettings()
        self.log = log if log is not None else SessionLog()
        s = self.settings.values
        self.timer = PomodoroTimer(
            focus_minutes=s["focus_minutes"],
            break_minutes=s["break_minutes"],
            long_break_minutes=s["long_break_minutes"],
        )
        self.sounds = SoundPlayer(self.settings)
        self.font = theme.pick_font_family(root)

        self._tick_id = None
        self._anim_id = None
        self._ambient_id = None
        self._bg_redraw_id = None
        self._last_tick_at = time.monotonic()
        self._remaining_at_tick = self.timer.remaining_seconds
        self._pulse_step = None
        self._current_view = "timer"
        self._focused = True

        root.title("Focus Timer — Midnight Glass")
        root.configure(bg=theme.BG_BOTTOM)
        root.geometry("1060x700")
        root.minsize(940, 620)

        self._build_chrome()
        self._build_timer_view()
        self._build_dashboard_view()
        self._build_settings_view()
        self._show_view("timer")
        self._refresh_all()
        self._start_ambient()
        if s["animations_enabled"]:
            self._fade_in()
        root.bind("<space>", self._on_space)
        root.bind("<FocusIn>", lambda e: setattr(self, "_focused", True))
        root.bind("<FocusOut>", lambda e: setattr(self, "_focused", False))

    # ------------------------------------------------------------------
    # chrome: gradient background, nav rail, view container
    # ------------------------------------------------------------------

    def _build_chrome(self):
        self.bg = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.bg.place(x=0, y=0, relwidth=1, relheight=1)
        self.bg.bind("<Configure>", self._on_bg_configure)

        self.nav = tk.Frame(self.root, bg=theme.GLASS,
                            highlightbackground=theme.GLASS_BORDER,
                            highlightthickness=1, width=104)
        self.nav.place(x=16, y=16, width=104)
        self.nav.bind("<Configure>", lambda e: None)
        self.root.bind("<Configure>", self._on_root_configure, add="+")

        tk.Label(self.nav, text="FOCUS", font=(self.font, 13, "bold"),
                 fg=theme.TEXT, bg=theme.GLASS).pack(pady=(18, 0))
        tk.Label(self.nav, text="TIMER", font=(self.font, 13, "bold"),
                 fg=theme.MUTED, bg=theme.GLASS).pack()
        tk.Frame(self.nav, bg=theme.GLASS_BORDER, height=1).pack(
            fill="x", padx=16, pady=16)

        self.nav_buttons = {}
        for key, label in (("timer", "Timer"), ("dashboard", "Dashboard"),
                           ("settings", "Settings")):
            btn = tk.Button(self.nav, text=label, font=(self.font, 11),
                            bg=theme.GLASS, fg=theme.MUTED, relief="flat",
                            activebackground=theme.GLASS_LIGHT,
                            activeforeground=theme.TEXT, cursor="hand2",
                            pady=9, bd=0, highlightthickness=0,
                            command=lambda k=key: self._show_view(k))
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[key] = btn

        self.container = tk.Frame(self.root, bg=STAGE_BG)
        self.container.place(x=136, y=16, relwidth=1, relheight=1,
                             width=-152, height=-32)
        self.views = {}

    def _on_root_configure(self, event):
        if event.widget is self.root:
            self.nav.place_configure(height=max(200, event.height - 32))

    def _on_bg_configure(self, event):
        if self._bg_redraw_id:
            self.root.after_cancel(self._bg_redraw_id)
        self._bg_redraw_id = self.root.after(
            120, lambda: self._draw_gradient(event.width, event.height))

    def _draw_gradient(self, width, height):
        self._bg_redraw_id = None
        self.bg.delete("grad")
        steps = 48
        colours = theme.gradient_steps(theme.BG_TOP, theme.BG_BOTTOM, steps)
        band = height / steps + 1
        for i, colour in enumerate(colours):
            self.bg.create_rectangle(0, i * band, width, (i + 1) * band,
                                     fill=colour, outline="", tags="grad")
        self.bg.tag_lower("grad")

    # ------------------------------------------------------------------
    # shared widget helpers
    # ------------------------------------------------------------------

    def _hover(self, widget, normal, hover):
        widget.bind("<Enter>", lambda e: widget.config(bg=hover))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal))

    def _glass_card(self, parent, title):
        card = tk.Frame(parent, bg=theme.GLASS,
                        highlightbackground=theme.GLASS_BORDER,
                        highlightthickness=1)
        tk.Label(card, text=title.upper(), font=(self.font, 9, "bold"),
                 fg=theme.FAINT, bg=theme.GLASS).pack(anchor="w", padx=16,
                                                      pady=(12, 2))
        return card

    def _primary_button(self, parent, text, command):
        colour = theme.blend(theme.BLUE, theme.VIOLET, 0.45)
        btn = tk.Button(parent, text=text, command=command,
                        font=(self.font, 13, "bold"), bg=colour, fg="white",
                        activebackground=theme.blend(theme.BLUE, theme.VIOLET, 0.2),
                        activeforeground="white", relief="flat", cursor="hand2",
                        padx=34, pady=10, bd=0, highlightthickness=0)
        self._hover(btn, colour, theme.blend(theme.BLUE, theme.VIOLET, 0.25))
        return btn

    def _ghost_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command,
                        font=(self.font, 11), bg=theme.GLASS, fg=theme.MUTED,
                        activebackground=theme.GLASS_LIGHT,
                        activeforeground=theme.TEXT, relief="flat",
                        cursor="hand2", padx=18, pady=9, bd=0,
                        highlightbackground=theme.GLASS_BORDER,
                        highlightthickness=1)
        self._hover(btn, theme.GLASS, theme.GLASS_LIGHT)
        return btn

    # ------------------------------------------------------------------
    # TIMER VIEW
    # ------------------------------------------------------------------

    def _build_timer_view(self):
        view = tk.Frame(self.container, bg=STAGE_BG)
        self.views["timer"] = view

        main = tk.Frame(view, bg=STAGE_BG)
        main.pack(side="left", fill="both", expand=True)

        self.stage = tk.Canvas(main, bg=STAGE_BG, highlightthickness=0, bd=0)
        self.stage.pack(fill="both", expand=True)
        self.stage.bind("<Configure>", lambda e: self._draw_stage())

        controls = tk.Frame(main, bg=STAGE_BG)
        controls.pack(pady=(2, 0))
        self.start_button = self._primary_button(controls, "Start",
                                                 self._toggle)
        self.start_button.pack(side="left", padx=6)
        self._ghost_button(controls, "Reset", self._reset).pack(
            side="left", padx=6)
        self._ghost_button(controls, "Skip", self._skip).pack(
            side="left", padx=6)

        self.status_label = tk.Label(main, text="Ready when you are.",
                                     font=(self.font, 11), fg=theme.MUTED,
                                     bg=STAGE_BG)
        self.status_label.pack(pady=(10, 14))

        side = tk.Frame(view, bg=STAGE_BG, width=248)
        side.pack(side="right", fill="y", padx=(6, 4), pady=10)
        side.pack_propagate(False)

        self.card_today = self._glass_card(side, "Today's focus")
        self.card_today.pack(fill="x", pady=(0, 12))
        self.today_value = self._card_value(self.card_today)
        self.today_sub = self._card_sub(self.card_today)

        self.card_streak = self._glass_card(side, "Streak")
        self.card_streak.pack(fill="x", pady=(0, 12))
        self.streak_value = self._card_value(self.card_streak)
        self.streak_sub = self._card_sub(self.card_streak)

        self.card_total = self._glass_card(side, "All time")
        self.card_total.pack(fill="x")
        self.total_value = self._card_value(self.card_total)
        self.total_sub = self._card_sub(self.card_total)

    def _card_value(self, card):
        label = tk.Label(card, text="—", font=(self.font, 24, "bold"),
                         fg=theme.TEXT, bg=theme.GLASS)
        label.pack(anchor="w", padx=16)
        return label

    def _card_sub(self, card):
        label = tk.Label(card, text="", font=(self.font, 10),
                         fg=theme.MUTED, bg=theme.GLASS)
        label.pack(anchor="w", padx=16, pady=(0, 12))
        return label

    # -- stage drawing ---------------------------------------------------

    def _draw_stage(self):
        c = self.stage
        w, h = c.winfo_width(), c.winfo_height()
        if w < 50 or h < 50:
            return
        c.delete("stage")
        steps = 40
        colours = theme.gradient_steps(theme.BG_TOP, STAGE_BG, steps)
        band = h / steps + 1
        for i, colour in enumerate(colours):
            c.create_rectangle(0, i * band, w, (i + 1) * band, fill=colour,
                               outline="", tags="stage")
        cx, cy = w // 2, h // 2 - 6
        radius = max(120, int(min(w, h) * 0.355))
        self._ring = (cx, cy, radius)
        self._draw_glow(cx, cy, radius)
        self._draw_ring(cx, cy, radius)
        self._draw_ring_texts(cx, cy, radius)

    def _draw_glow(self, cx, cy, radius):
        c = self.stage
        c.delete("glow")
        self._glow_offset = (0, 0)
        mode_colour = theme.MODE_GRADIENTS[self.timer.mode][1]
        for i in range(10, 0, -1):
            r = radius + 10 + i * 5
            colour = theme.blend(STAGE_BG, mode_colour, 0.015 * (11 - i))
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colour,
                          outline="", tags=("stage", "glow"))

    def _draw_ring(self, cx, cy, radius):
        c = self.stage
        c.delete("ring")
        c.create_oval(cx - radius, cy - radius, cx + radius, cy + radius,
                      outline=theme.TRACK, width=13, tags=("stage", "ring"))
        start_colour, end_colour = theme.MODE_GRADIENTS[self.timer.mode]
        colours = theme.gradient_steps(start_colour, end_colour, SEGMENTS)
        self._segment_ids = []
        for i in range(SEGMENTS):
            a0 = 90 - i * (360 / SEGMENTS)
            a1 = 90 - (i + 1) * (360 / SEGMENTS) - 0.8
            item = c.create_arc(cx - radius, cy - radius, cx + radius,
                                cy + radius, start=a0, extent=-(a0 - a1),
                                style="arc", outline=colours[i], width=13,
                                tags=("stage", "ring"))
            self._segment_ids.append(item)
        self._update_ring(self.timer.progress)

    def _draw_ring_texts(self, cx, cy, radius):
        c = self.stage
        c.delete("ringtext")
        big = max(30, int(radius * 0.46))
        self._time_text = c.create_text(
            cx, cy - 8, text=self.timer.display(), fill=theme.TEXT,
            font=(self.font, big), tags=("stage", "ringtext"))
        self._mode_text = c.create_text(
            cx, cy - radius * 0.52,
            text=theme.MODE_LABELS[self.timer.mode], fill=theme.MUTED,
            font=(self.font, 13, "bold"), tags=("stage", "ringtext"))
        cycle = self.timer.sessions_before_long_break
        done = self.timer.completed_focus_sessions
        pos = done % cycle
        if self.timer.mode == LONG_BREAK:
            pos = cycle
        if self.timer.mode == FOCUS:
            session_line = f"SESSION {pos + 1} OF {cycle}"
        elif self.timer.mode == LONG_BREAK:
            session_line = "LONG BREAK — RECHARGE"
        else:
            session_line = "BREAK TIME"
        self._session_text = c.create_text(
            cx, cy + radius * 0.40, text=session_line,
            fill=theme.FAINT, font=(self.font, 10, "bold"),
            tags=("stage", "ringtext"))
        self._dot_ids = []
        dot_r, gap = 5.5, 26
        x0 = cx - (cycle - 1) * gap / 2
        unfilled = theme.blend(theme.TRACK, theme.MUTED, 0.35)
        for i in range(cycle):
            filled = i < pos
            item = c.create_oval(x0 + i * gap - dot_r, cy + radius * 0.55 - dot_r,
                                 x0 + i * gap + dot_r, cy + radius * 0.55 + dot_r,
                                 fill=theme.VIOLET if filled else unfilled,
                                 outline="", tags=("stage", "ringtext"))
            self._dot_ids.append(item)

    def _update_ring(self, progress):
        if not hasattr(self, "_segment_ids"):
            return
        visible = int(round(progress * SEGMENTS))
        for i, item in enumerate(self._segment_ids):
            self.stage.itemconfig(item, state="normal" if i < visible else "hidden")
        if hasattr(self, "_time_text"):
            self.stage.itemconfig(self._time_text, text=self.timer.display())

    # ------------------------------------------------------------------
    # DASHBOARD VIEW
    # ------------------------------------------------------------------

    def _build_dashboard_view(self):
        view = tk.Frame(self.container, bg=STAGE_BG)
        self.views["dashboard"] = view

        tk.Label(view, text="Productivity Dashboard",
                 font=(self.font, 20, "bold"), fg=theme.TEXT,
                 bg=STAGE_BG).pack(anchor="w", padx=26, pady=(22, 4))
        tk.Label(view, text="Your focus, at a glance.",
                 font=(self.font, 11), fg=theme.MUTED,
                 bg=STAGE_BG).pack(anchor="w", padx=26, pady=(0, 16))

        cards = tk.Frame(view, bg=STAGE_BG)
        cards.pack(fill="x", padx=26)
        self.dash_cards = {}
        for key, title in (("today_sessions", "Sessions today"),
                           ("today_minutes", "Minutes today"),
                           ("streak", "Day streak"),
                           ("best", "Best day")):
            card = self._glass_card(cards, title)
            card.pack(side="left", fill="x", expand=True,
                      padx=(0, 12) if key != "best" else (0, 0))
            value = tk.Label(card, text="—", font=(self.font, 20, "bold"),
                             fg=theme.TEXT, bg=theme.GLASS)
            value.pack(anchor="w", padx=16, pady=(0, 12))
            self.dash_cards[key] = value

        self.daily_canvas = self._bar_panel(view, "Last 7 days")
        self.weekly_canvas = self._bar_panel(view, "Last 4 weeks")

        row = tk.Frame(view, bg=STAGE_BG)
        row.pack(anchor="w", padx=26, pady=(14, 0))
        self._ghost_button(row, "Export PNG charts",
                           self._export_charts).pack(side="left")
        self.dash_status = tk.Label(row, text="", font=(self.font, 10),
                                    fg=theme.MUTED, bg=STAGE_BG)
        self.dash_status.pack(side="left", padx=14)

    def _bar_panel(self, parent, title):
        panel = self._glass_card(parent, title)
        panel.pack(fill="x", padx=26, pady=(14, 0))
        canvas = tk.Canvas(panel, bg=theme.GLASS, highlightthickness=0,
                           bd=0, height=118)
        canvas.pack(fill="x", padx=12, pady=(2, 10))
        canvas.bind("<Configure>", lambda e: self._refresh_dashboard())
        return canvas

    def _draw_bars(self, canvas, rows):
        canvas.delete("bars")
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w < 60 or not rows:
            return
        max_minutes = max([m for _, m in rows] + [1])
        slot = w / len(rows)
        bar_w = min(64, slot * 0.52)
        base = h - 24
        for i, (label, minutes) in enumerate(rows):
            cx = slot * i + slot / 2
            bar_h = (base - 22) * minutes / max_minutes if minutes else 0
            colour = theme.VIOLET if i == len(rows) - 1 else theme.BLUE
            if minutes:
                self._rounded_bar(canvas, cx - bar_w / 2, base - bar_h,
                                  cx + bar_w / 2, base, 6, colour)
                canvas.create_text(cx, base - bar_h - 9, text=str(minutes),
                                   fill=theme.TEXT, font=(self.font, 9, "bold"),
                                   tags="bars")
            canvas.create_text(cx, base + 12, text=label, fill=theme.MUTED,
                               font=(self.font, 9), tags="bars")

    def _rounded_bar(self, canvas, x0, y0, x1, y1, r, colour):
        canvas.create_rectangle(x0, y0 + r, x1, y1, fill=colour, outline="",
                                tags="bars")
        canvas.create_oval(x0, y0, x0 + 2 * r, y0 + 2 * r, fill=colour,
                           outline="", tags="bars")
        canvas.create_oval(x1 - 2 * r, y0, x1, y0 + 2 * r, fill=colour,
                           outline="", tags="bars")
        canvas.create_rectangle(x0 + r, y0, x1 - r, y0 + r, fill=colour,
                                outline="", tags="bars")

    def _export_charts(self):
        out_dir = Path(__file__).resolve().parent.parent / "charts"
        daily, weekly = charts.make_charts(self.log, out_dir)
        self.dash_status.config(
            text=f"Saved daily_chart.png + weekly_chart.png to {out_dir}")

    # ------------------------------------------------------------------
    # SETTINGS VIEW
    # ------------------------------------------------------------------

    def _build_settings_view(self):
        view = tk.Frame(self.container, bg=STAGE_BG)
        self.views["settings"] = view
        s = self.settings.values

        tk.Label(view, text="Settings", font=(self.font, 20, "bold"),
                 fg=theme.TEXT, bg=STAGE_BG).pack(anchor="w", padx=26,
                                                  pady=(22, 16))

        durations = self._glass_card(view, "Session durations (minutes)")
        durations.pack(fill="x", padx=26)
        grid = tk.Frame(durations, bg=theme.GLASS)
        grid.pack(anchor="w", padx=16, pady=(4, 6))
        self.duration_vars = {}
        for col, (key, label) in enumerate((
                ("focus_minutes", "Focus"), ("break_minutes", "Short break"),
                ("long_break_minutes", "Long break"))):
            tk.Label(grid, text=label, font=(self.font, 10), fg=theme.MUTED,
                     bg=theme.GLASS).grid(row=0, column=col * 2, padx=(0, 6),
                                          pady=4, sticky="w")
            var = tk.StringVar(value=str(s[key]))
            spin = tk.Spinbox(grid, from_=config.MIN_MINUTES,
                              to=config.MAX_MINUTES, width=5,
                              textvariable=var, font=(self.font, 12),
                              bg=theme.BG_TOP, fg=theme.TEXT,
                              buttonbackground=theme.GLASS_LIGHT,
                              insertbackground=theme.TEXT, relief="flat")
            spin.grid(row=0, column=col * 2 + 1, padx=(0, 22), pady=4)
            self.duration_vars[key] = var
        row = tk.Frame(durations, bg=theme.GLASS)
        row.pack(anchor="w", padx=16, pady=(2, 14))
        self._ghost_button(row, "Apply durations",
                           self._apply_durations).pack(side="left")
        self.settings_status = tk.Label(row, text="", font=(self.font, 10),
                                        fg=theme.MUTED, bg=theme.GLASS)
        self.settings_status.pack(side="left", padx=14)

        sound = self._glass_card(view, "Sound")
        sound.pack(fill="x", padx=26, pady=(14, 0))
        srow = tk.Frame(sound, bg=theme.GLASS)
        srow.pack(anchor="w", padx=16, pady=(4, 14))
        self.sound_toggle = self._ghost_button(srow, "", self._toggle_sound)
        self.sound_toggle.pack(side="left")
        tk.Label(srow, text="Volume", font=(self.font, 10), fg=theme.MUTED,
                 bg=theme.GLASS).pack(side="left", padx=(22, 8))
        self.volume_var = tk.IntVar(value=s["volume"])
        scale = tk.Scale(srow, from_=0, to=100, orient="horizontal",
                         variable=self.volume_var, length=190,
                         bg=theme.GLASS, fg=theme.TEXT,
                         troughcolor=theme.TRACK, highlightthickness=0,
                         bd=0, sliderrelief="flat", showvalue=False,
                         command=lambda v: self.volume_label.config(
                             text=f"{int(float(v))}%"))
        scale.pack(side="left")
        scale.bind("<ButtonRelease-1>", self._save_volume)
        self.volume_label = tk.Label(srow, text=f"{s['volume']}%",
                                     font=(self.font, 10), fg=theme.TEXT,
                                     bg=theme.GLASS, width=5)
        self.volume_label.pack(side="left", padx=(6, 16))
        self._ghost_button(srow, "Test sound",
                           self._test_sound).pack(side="left")
        self._refresh_sound_toggle()

        motion = self._glass_card(view, "Motion")
        motion.pack(fill="x", padx=26, pady=(14, 0))
        mrow = tk.Frame(motion, bg=theme.GLASS)
        mrow.pack(anchor="w", padx=16, pady=(4, 14))
        tk.Label(mrow, text="Animations", font=(self.font, 10),
                 fg=theme.MUTED, bg=theme.GLASS).pack(side="left")
        self.anim_toggle = self._ghost_button(mrow, "",
                                              self._toggle_animations)
        self.anim_toggle.pack(side="left", padx=(8, 24))
        tk.Label(mrow, text="Ambient lighting motion", font=(self.font, 10),
                 fg=theme.MUTED, bg=theme.GLASS).pack(side="left")
        self.ambient_toggle = self._ghost_button(mrow, "",
                                                 self._toggle_ambient)
        self.ambient_toggle.pack(side="left", padx=(8, 0))
        self._refresh_motion_toggles()

        tk.Label(view, text="Preferences save automatically to "
                            "data/settings.json. Session history is stored "
                            "separately and is never changed by settings.",
                 font=(self.font, 9), fg=theme.FAINT,
                 bg=STAGE_BG).pack(anchor="w", padx=26, pady=(16, 0))

    def _refresh_sound_toggle(self):
        on = self.settings.get("sound_enabled")
        self.sound_toggle.config(text="Sound: On" if on else "Sound: Off",
                                 fg=theme.TEXT if on else theme.MUTED)

    def _refresh_motion_toggles(self):
        a = self.settings.get("animations_enabled")
        m = self.settings.get("ambient_motion")
        self.anim_toggle.config(text="On" if a else "Off",
                                fg=theme.TEXT if a else theme.MUTED)
        self.ambient_toggle.config(text="On" if m else "Off",
                                   fg=theme.TEXT if m else theme.MUTED)

    def _toggle_sound(self):
        self.settings.set("sound_enabled",
                          not self.settings.get("sound_enabled"))
        self._refresh_sound_toggle()

    def _save_volume(self, event=None):
        self.settings.set("volume", int(self.volume_var.get()))

    def _test_sound(self):
        if not self.sounds.play("focus_complete"):
            if self.settings.get("sound_enabled"):
                self.root.bell()  # non-Windows fallback
                self.settings_status.config(text="")
            else:
                self.settings_status.config(
                    text="Sound is off — turn it on to hear the test.",
                    fg=ERROR)
                return
        self.settings_status.config(text="")

    def _toggle_animations(self):
        self.settings.set("animations_enabled",
                          not self.settings.get("animations_enabled"))
        self._refresh_motion_toggles()
        if self.settings.get("animations_enabled"):
            self._start_anim_loop()
        elif self._anim_id:
            self.root.after_cancel(self._anim_id)
            self._anim_id = None
            self._update_ring(self.timer.progress)

    def _toggle_ambient(self):
        self.settings.set("ambient_motion",
                          not self.settings.get("ambient_motion"))
        self._refresh_motion_toggles()

    def _apply_durations(self):
        try:
            values = {k: int(v.get()) for k, v in self.duration_vars.items()}
            new_timer = PomodoroTimer(
                focus_minutes=values["focus_minutes"],
                break_minutes=values["break_minutes"],
                long_break_minutes=values["long_break_minutes"])
        except (ValueError, TypeError):
            self.settings_status.config(
                text=f"Minutes must be whole numbers between "
                     f"{config.MIN_MINUTES} and {config.MAX_MINUTES}.",
                fg=ERROR)
            return
        new_timer.completed_focus_sessions = \
            self.timer.completed_focus_sessions
        self._cancel_tick()
        self.timer = new_timer
        self._remaining_at_tick = self.timer.remaining_seconds
        for key, value in values.items():
            self.settings.set(key, value)
        self.settings_status.config(
            text="Durations applied and saved.", fg=theme.MUTED)
        self._draw_stage()
        self._refresh_all()

    # ------------------------------------------------------------------
    # view switching + entrance
    # ------------------------------------------------------------------

    def _show_view(self, key):
        self._current_view = key
        view = self.views[key]
        view.place(x=0, y=0, relwidth=1, relheight=1)
        view.tkraise()
        for name, btn in self.nav_buttons.items():
            active = name == key
            btn.config(bg=theme.GLASS_LIGHT if active else theme.GLASS,
                       fg=theme.TEXT if active else theme.MUTED,
                       font=(self.font, 11, "bold") if active
                       else (self.font, 11))
        if key == "dashboard":
            self._refresh_dashboard()
        if key == "timer" and self.timer.state == "running":
            self._start_anim_loop()
        if self.settings.get("animations_enabled"):
            self._slide_in(view)

    def _slide_in(self, view):
        for step, offset in enumerate((10, 6, 3, 0)):
            self.root.after(step * 22,
                            lambda o=offset: view.place_configure(y=o))

    def _fade_in(self):
        try:
            self.root.attributes("-alpha", 0.0)
        except tk.TclError:
            return

        def step(value):
            try:
                self.root.attributes("-alpha", value)
            except tk.TclError:
                return
            if value < 1.0:
                self.root.after(24, lambda: step(min(1.0, value + 0.14)))

        self.root.after(24, lambda: step(0.14))

    # ------------------------------------------------------------------
    # timer actions
    # ------------------------------------------------------------------

    def _on_space(self, event):
        if event.widget.__class__.__name__ in ("Spinbox", "Scale", "Entry"):
            return
        if self._current_view == "timer":
            self._toggle()

    def _toggle(self):
        was_running = self.timer.state == "running"
        self.timer.toggle()
        if self.timer.state == "running":
            if not self.sounds.play("start"):
                pass
            self.status_label.config(
                text="Focusing..." if self.timer.mode == FOCUS
                else "On a break.")
            self._last_tick_at = time.monotonic()
            self._remaining_at_tick = self.timer.remaining_seconds
            self._schedule_tick()
            self._start_anim_loop()
        else:
            self.sounds.play("pause")
            self.status_label.config(text="Paused.")
            self._cancel_tick()
        self._refresh_all()

    def _reset(self):
        self._cancel_tick()
        self.timer.reset()
        self._remaining_at_tick = self.timer.remaining_seconds
        self.status_label.config(text="Reset. Ready when you are.")
        self._draw_stage()
        self._refresh_all()

    def _skip(self):
        self._cancel_tick()
        finished = self.timer.skip()
        self._remaining_at_tick = self.timer.remaining_seconds
        self.status_label.config(
            text="Focus skipped — not counted. Break is ready."
            if finished == FOCUS else "Break skipped. Focus is ready.")
        self._draw_stage()
        self._refresh_all()

    # ------------------------------------------------------------------
    # ticking + animation loops (accuracy: core ticks exactly 1/sec)
    # ------------------------------------------------------------------

    def _schedule_tick(self):
        self._cancel_tick()
        self._tick_id = self.root.after(1000, self._tick)

    def _cancel_tick(self):
        if self._tick_id is not None:
            try:
                self.root.after_cancel(self._tick_id)
            except Exception:
                pass
            self._tick_id = None

    def _tick(self):
        self._tick_id = None
        event = self.timer.tick()
        self._last_tick_at = time.monotonic()
        self._remaining_at_tick = self.timer.remaining_seconds
        if event == "focus_completed":
            minutes = self.timer.focus_seconds // 60
            self.log.add_session(minutes)
            self._play_completion("focus_complete")
            self.status_label.config(
                text=f"Focus session saved: +{minutes} min. Take your break.")
            self._pulse()
            self._draw_stage()
        elif event in ("break_completed", "long_break_completed"):
            self._play_completion("break_complete")
            self.status_label.config(text="Break over. Ready to focus again?")
            self._pulse()
            self._draw_stage()
        self._refresh_all()
        if self.timer.state == "running":
            self._schedule_tick()

    def _play_completion(self, name):
        if not self.sounds.play(name) and self.settings.get("sound_enabled"):
            try:
                self.root.bell()
            except Exception:
                pass

    def _start_anim_loop(self):
        if self._anim_id is not None or not self.settings.get(
                "animations_enabled"):
            return
        self._anim_id = self.root.after(50, self._anim_step)

    def _anim_step(self):
        self._anim_id = None
        if self.timer.state == "running" and self._current_view == "timer":
            elapsed = time.monotonic() - self._last_tick_at
            smooth_remaining = max(0.0, self._remaining_at_tick - elapsed)
            total = self.timer.total_seconds_for_mode or 1
            self._update_ring(1.0 - smooth_remaining / total)
            self._anim_id = self.root.after(50, self._anim_step)

    def _pulse(self):
        if not self.settings.get("animations_enabled") or not hasattr(
                self, "_ring"):
            return
        self._pulse_step = 0
        self._pulse_frame()

    def _pulse_frame(self):
        if self._pulse_step is None or not hasattr(self, "_ring"):
            return
        cx, cy, radius = self._ring
        step = self._pulse_step
        self.stage.delete("pulse")
        if step >= 7:
            self._pulse_step = None
            return
        colour = theme.blend(STAGE_BG,
                             theme.MODE_GRADIENTS[self.timer.mode][1],
                             0.35 * (1 - step / 7))
        r = radius + 20 + step * 9
        self.stage.create_oval(cx - r, cy - r, cx + r, cy + r,
                               outline=colour, width=2, tags="pulse")
        self._pulse_step = step + 1
        self.root.after(55, self._pulse_frame)

    def _start_ambient(self):
        if self._ambient_id is None:
            self._ambient_id = self.root.after(140, self._ambient_step)

    def _ambient_step(self):
        self._ambient_id = None
        if (self.settings.get("animations_enabled")
                and self.settings.get("ambient_motion")
                and self._current_view == "timer" and self._focused):
            t = time.monotonic()
            dx = int(6 * _sin(t / 9.0))
            dy = int(4 * _sin(t / 13.0 + 1.3))
            if hasattr(self, "_glow_offset"):
                ox, oy = self._glow_offset
                self.stage.move("glow", dx - ox, dy - oy)
            self._glow_offset = (dx, dy)
        self._ambient_id = self.root.after(140, self._ambient_step)

    # ------------------------------------------------------------------
    # refresh
    # ------------------------------------------------------------------

    def _refresh_all(self):
        t = self.timer
        self.start_button.config(
            text="Pause" if t.state == "running" else
            "Resume" if t.state == "paused" else "Start")
        if hasattr(self, "_segment_ids"):
            self._draw_ring_texts(*self._ring) if hasattr(self, "_ring") \
                else None
            self._update_ring(t.progress)
        s = stats.summary(self.log)
        self.today_value.config(text=f"{s['today_minutes']} min")
        self.today_sub.config(text=f"{s['today_sessions']} sessions completed")
        self.streak_value.config(text=f"{s['streak']} day"
                                 + ("s" if s['streak'] != 1 else ""))
        self.streak_sub.config(text="one session a day")
        self.total_value.config(text=f"{s['total_minutes']} min")
        self.total_sub.config(text=f"{s['total_sessions']} sessions all time")
        if self._current_view == "dashboard":
            self._refresh_dashboard()

    def _refresh_dashboard(self):
        if not hasattr(self, "dash_cards"):
            return
        s = stats.summary(self.log)
        self.dash_cards["today_sessions"].config(
            text=str(s["today_sessions"]))
        self.dash_cards["today_minutes"].config(
            text=str(s["today_minutes"]))
        self.dash_cards["streak"].config(text=str(s["streak"]))
        self.dash_cards["best"].config(
            text=f"{s['best_day_minutes']} min" if s["best_day"] else "—")
        self._draw_bars(self.daily_canvas,
                        [(d.strftime("%a"), m)
                         for d, m, _ in stats.daily_totals(self.log)])
        self._draw_bars(self.weekly_canvas,
                        [(d.strftime("%d %b"), m)
                         for d, m, _ in stats.weekly_totals(self.log)])


def _sin(x):
    import math

    return math.sin(x)


def main():
    root = tk.Tk()
    FocusTimerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
