"""Dashboard charts as PNG files, drawn with matplotlib (Agg backend).

The GUI shows live numbers itself; these PNGs are the shareable
dashboard — open them, send them, put them in a report.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import stats  # noqa: E402

VIOLET = "#7C3AED"
VIOLET_LIGHT = "#A78BFA"
GREY = "#9CA3AF"


def daily_chart(log, out_path, days=7, today=None):
    rows = stats.daily_totals(log, days=days, today=today)
    labels = [d.strftime("%a") for d, _, _ in rows]
    minutes = [m for _, m, _ in rows]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.bar(labels, minutes, color=VIOLET, edgecolor="none")
    if minutes:
        bars[-1].set_color(VIOLET_LIGHT)  # today stands out
    for bar, value in zip(bars, minutes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(value), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Focus minutes")
    ax.set_title("Focus minutes — last 7 days")
    ax.set_ylim(0, max(minutes + [30]) * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def weekly_chart(log, out_path, weeks=4, today=None):
    rows = stats.weekly_totals(log, weeks=weeks, today=today)
    labels = [d.strftime("%d %b") for d, _, _ in rows]
    minutes = [m for _, m, _ in rows]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    bars = ax.bar(labels, minutes, color=VIOLET, edgecolor="none")
    if minutes:
        bars[-1].set_color(VIOLET_LIGHT)  # current week stands out
    for bar, value in zip(bars, minutes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                str(value), ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Focus minutes")
    ax.set_xlabel("Week starting (Monday)")
    ax.set_title("Focus minutes — last 4 weeks")
    ax.set_ylim(0, max(minutes + [60]) * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def make_charts(log, out_dir, today=None):
    out_dir = Path(out_dir)
    return (
        daily_chart(log, out_dir / "daily_chart.png", today=today),
        weekly_chart(log, out_dir / "weekly_chart.png", today=today),
    )
