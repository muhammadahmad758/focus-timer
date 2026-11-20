"""User preferences — a small JSON file next to the session log.

Holds sound, animation and duration preferences. Session history lives
in its own file (storage.py) and is never touched by this module.
A missing or corrupt settings file falls back to defaults.
"""

import json
import os
from pathlib import Path

from . import config

SETTINGS_FILENAME = "settings.json"

DEFAULTS = {
    "sound_enabled": True,
    "volume": 70,               # 0..100
    "animations_enabled": True,
    "ambient_motion": True,
    "focus_minutes": config.DEFAULT_FOCUS_MINUTES,
    "break_minutes": config.DEFAULT_BREAK_MINUTES,
    "long_break_minutes": config.DEFAULT_LONG_BREAK_MINUTES,
}


def default_settings_path(base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent / "data"
    return base / SETTINGS_FILENAME


def _clean(raw):
    out = dict(DEFAULTS)
    if not isinstance(raw, dict):
        return out
    for key in ("sound_enabled", "animations_enabled", "ambient_motion"):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    if isinstance(raw.get("volume"), (int, float)):
        out["volume"] = max(0, min(100, int(raw["volume"])))
    for key in ("focus_minutes", "break_minutes", "long_break_minutes"):
        value = raw.get(key)
        if isinstance(value, (int, float)) and config.MIN_MINUTES <= int(value) <= config.MAX_MINUTES:
            out[key] = int(value)
    return out


class AppSettings:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_settings_path()
        self.values = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            self.values = _clean(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            self.values = dict(DEFAULTS)
        return self.values

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.values, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def get(self, key):
        return self.values[key]

    def set(self, key, value):
        self.values = _clean({**self.values, key: value})
        self.save()
