"""Session storage — a small JSON file that survives restarts.

One record per completed focus session:
    {"date": "2026-11-20", "minutes": 25, "ended_at": "15:30:05"}

Writes are atomic (temp file + replace), and a missing or corrupt file
never crashes the app — it simply starts with an empty log.
"""

import json
import os
from datetime import date, datetime
from pathlib import Path

from . import config


def default_data_path(base_dir=None):
    base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent / "data"
    return base / config.DATA_FILENAME


class SessionLog:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_data_path()
        self.sessions = []
        self.load()

    # -- persistence ------------------------------------------------------

    def load(self):
        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, ValueError):
            self.sessions = []
            return 0
        if not isinstance(data, list):
            self.sessions = []
            return 0
        clean = []
        for item in data:
            if (
                isinstance(item, dict)
                and isinstance(item.get("date"), str)
                and isinstance(item.get("minutes"), (int, float))
            ):
                clean.append(
                    {
                        "date": item["date"],
                        "minutes": int(item["minutes"]),
                        "ended_at": str(item.get("ended_at", "")),
                    }
                )
        self.sessions = clean
        return len(clean)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.sessions, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    # -- recording ----------------------------------------------------------

    def add_session(self, minutes, when=None):
        """Record one completed focus session. Returns the record."""
        when = when or datetime.now()
        record = {
            "date": when.date().isoformat(),
            "minutes": int(minutes),
            "ended_at": when.strftime("%H:%M:%S"),
        }
        self.sessions.append(record)
        self.save()
        return record

    # -- queries ------------------------------------------------------------

    def sessions_on(self, day):
        day = day.isoformat() if isinstance(day, date) else str(day)
        return [s for s in self.sessions if s["date"] == day]

    def minutes_on(self, day):
        return sum(s["minutes"] for s in self.sessions_on(day))

    def total_minutes(self):
        return sum(s["minutes"] for s in self.sessions)

    def total_sessions(self):
        return len(self.sessions)
