"""Dashboard charts as PNG files, drawn with matplotlib (Agg backend).

Midnight Glass styling: deep navy figure, electric-blue bars with the
current day/week in violet, soft white text. Same API as v1.0.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import stats  # noqa: E402

BG = "#0D1526"
PANEL = "#141F38"
BLUE = "#4F8CFF"
VIOLET = "#7C5CFF"
TEXT = "#F4F7FF"
MUTED = "#93A0B8"
GRID = "#2A3D66"


def _style(ax):
    ax.set_facecolor(PANEL)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.label.set_color(MUTED)
    ax.title.set_color(TEXT)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)


def _finish(fig, ax, labels, minutes, ylabel, title, floor):
    bars = ax.bar(labels, minutes, color=BLUE, edgecolor="none", width=0.58)
    if len(bars):
        bars[-1].set_color(VIOLET)  # today / current week stands out
    for bar, value in zip(bars, minutes):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                str(value), ha="center", va="bottom", fontsize=9, color=TEXT)
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=12, pad=12)
    ax.set_ylim(0, max(minutes + [floor]) * 1.2)
    _style(ax)
    fig.tight_layout()


def daily_chart(log, out_path, days=7, today=None):
    rows = stats.daily_totals(log, days=days, today=today)
    labels = [d.strftime("%a") for d, _, _ in rows]
    minutes = [m for _, m, _ in rows]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    fig.patch.set_facecolor(BG)
    _finish(fig, ax, labels, minutes, "Focus minutes",
            "Focus minutes — last 7 days", 30)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor=BG)
    plt.close(fig)
    return out_path


def weekly_chart(log, out_path, weeks=4, today=None):
    rows = stats.weekly_totals(log, weeks=weeks, today=today)
    labels = [d.strftime("%d %b") for d, _, _ in rows]
    minutes = [m for _, m, _ in rows]
    fig, ax = plt.subplots(figsize=(7, 3.4))
    fig.patch.set_facecolor(BG)
    _finish(fig, ax, labels, minutes, "Focus minutes",
            "Focus minutes — last 4 weeks", 60)
    ax.set_xlabel("Week starting (Monday)", color=MUTED)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, facecolor=BG)
    plt.close(fig)
    return out_path


def make_charts(log, out_dir, today=None):
    out_dir = Path(out_dir)
    return (
        daily_chart(log, out_dir / "daily_chart.png", today=today),
        weekly_chart(log, out_dir / "weekly_chart.png", today=today),
    )
