"""Midnight Glass theme — palette, fonts and small colour helpers.

Tkinter cannot do true translucent blur, so the glass look is simulated:
layered navy panels with hairline light borders over a gradient
background with a restrained ambient glow. All colours live here so
the whole app stays consistent.
"""

import tkinter as tk
import tkinter.font as tkfont

# -- palette ---------------------------------------------------------------
BG_TOP = "#0D1526"        # midnight navy, top of the gradient
BG_BOTTOM = "#070A14"     # near-black charcoal, bottom
GLASS = "#141F38"         # panel surface (simulated glass)
GLASS_LIGHT = "#1B2A4A"   # panel surface on hover / emphasis
GLASS_BORDER = "#2A3D66"  # hairline border
TRACK = "#1A2745"         # ring track / bar track

TEXT = "#F4F7FF"
MUTED = "#93A0B8"
FAINT = "#5D6B87"

BLUE = "#4F8CFF"
VIOLET = "#7C5CFF"
TEAL = "#2DD4BF"
GREEN = "#34D399"

# Ring gradient per mode: (start colour, end colour)
MODE_GRADIENTS = {
    "focus": (BLUE, VIOLET),
    "break": ("#34D399", TEAL),
    "long_break": (VIOLET, "#B18CFF"),
}
MODE_LABELS = {
    "focus": "FOCUS",
    "break": "SHORT BREAK",
    "long_break": "LONG BREAK",
}

FONT_CANDIDATES = (
    "Segoe UI Variable Display",
    "Segoe UI Variable Text",
    "Segoe UI",
    "Helvetica Neue",
    "Helvetica",
    "Arial",
)


def pick_font_family(root):
    """Best available UI font: Segoe UI Variable on Windows 11 first."""
    try:
        available = set(tkfont.families(root))
    except tk.TclError:
        return "Segoe UI"
    for name in FONT_CANDIDATES:
        if name in available:
            return name
    return "TkDefaultFont"


def hex_to_rgb(colour):
    colour = colour.lstrip("#")
    return tuple(int(colour[i:i + 2], 16) for i in (0, 2, 4))


def blend(colour_a, colour_b, t):
    """Colour between A (t=0) and B (t=1), as a hex string."""
    a, b = hex_to_rgb(colour_a), hex_to_rgb(colour_b)
    out = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    return "#%02x%02x%02x" % out


def gradient_steps(colour_a, colour_b, steps):
    if steps <= 1:
        return [colour_a]
    return [blend(colour_a, colour_b, i / (steps - 1)) for i in range(steps)]
