"""Productivity statistics — pure functions over a SessionLog.

Everything here takes plain dates so it can be tested with fixed data:
daily totals, weekly totals, and the streak (consecutive days, ending
today or yesterday, with at least one completed focus session).
"""

from datetime import date, timedelta


def daily_totals(log, days=7, today=None):
    """[(date, minutes, sessions), ...] for the last `days` days, oldest first."""
    today = today or date.today()
    out = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        out.append((day, log.minutes_on(day), len(log.sessions_on(day))))
    return out


def weekly_totals(log, weeks=4, today=None):
    """[(week_start_date, minutes, sessions), ...], oldest first.

    Weeks start on Monday. The last entry is the current week so far.
    """
    today = today or date.today()
    this_monday = today - timedelta(days=today.weekday())
    out = []
    for back in range(weeks - 1, -1, -1):
        start = this_monday - timedelta(weeks=back)
        minutes = 0
        sessions = 0
        for i in range(7):
            day = start + timedelta(days=i)
            if day > today:
                break
            minutes += log.minutes_on(day)
            sessions += len(log.sessions_on(day))
        out.append((start, minutes, sessions))
    return out


def current_streak(log, today=None):
    """Consecutive days with >= 1 session, ending today or yesterday.

    If today has no session yet, the streak can still be alive from
    yesterday — it only breaks after a full day is missed.
    """
    today = today or date.today()
    active_days = {s["date"] for s in log.sessions}
    cursor = today
    if cursor.isoformat() not in active_days:
        cursor -= timedelta(days=1)
        if cursor.isoformat() not in active_days:
            return 0
    streak = 0
    while cursor.isoformat() in active_days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def best_day(log):
    """(date_string, minutes) for the biggest day, or (None, 0) if empty."""
    totals = {}
    for s in log.sessions:
        totals[s["date"]] = totals.get(s["date"], 0) + s["minutes"]
    if not totals:
        return None, 0
    day = max(totals, key=totals.get)
    return day, totals[day]


def summary(log, today=None):
    today = today or date.today()
    best_date, best_minutes = best_day(log)
    return {
        "today_minutes": log.minutes_on(today),
        "today_sessions": len(log.sessions_on(today)),
        "total_minutes": log.total_minutes(),
        "total_sessions": log.total_sessions(),
        "streak": current_streak(log, today=today),
        "best_day": best_date,
        "best_day_minutes": best_minutes,
    }
