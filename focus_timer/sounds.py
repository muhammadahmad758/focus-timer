"""Original, locally generated sounds — no downloads, fully offline.

The WAV files in ``assets/sounds/`` are synthesized with the standard
library only (sine tones with a soft fade envelope), so they are
original and licence-free. Playback uses winsound on Windows; on other
systems it falls back to the terminal bell. Volume is applied by
rendering a scaled copy of the WAV into ``data/sound_cache/`` —
winsound itself has no volume control.
"""

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 44100

# name -> list of (frequency Hz, start s, duration s, peak amplitude)
RECIPES = {
    "start": [(660.0, 0.0, 0.12, 0.35)],
    "pause": [(520.0, 0.0, 0.10, 0.30)],
    "focus_complete": [(659.25, 0.0, 0.35, 0.40), (987.77, 0.16, 0.55, 0.40)],
    "break_complete": [(783.99, 0.0, 0.30, 0.38), (587.33, 0.14, 0.50, 0.38)],
}


def sounds_dir():
    return Path(__file__).resolve().parent.parent / "assets" / "sounds"


def render_recipe(recipe, volume=1.0):
    """Return 16-bit mono PCM samples for a recipe at the given volume."""
    total_seconds = max(start + dur for _, start, dur, _ in recipe) + 0.05
    total = int(total_seconds * SAMPLE_RATE)
    samples = [0.0] * total
    for freq, start, dur, peak in recipe:
        first = int(start * SAMPLE_RATE)
        count = int(dur * SAMPLE_RATE)
        for i in range(count):
            t = i / SAMPLE_RATE
            # smooth attack/decay so the tone never clicks
            envelope = math.sin(math.pi * i / count) ** 1.5
            idx = first + i
            if idx < total:
                samples[idx] += peak * envelope * math.sin(2 * math.pi * freq * t)
    out = []
    for value in samples:
        value = max(-1.0, min(1.0, value * volume))
        out.append(int(value * 32767))
    return out


def write_wav(path, samples):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(b"".join(struct.pack("<h", s) for s in samples))
    return path


def ensure_sounds(directory=None):
    """Generate any missing sound files. Returns {name: path}."""
    directory = Path(directory) if directory else sounds_dir()
    paths = {}
    for name, recipe in RECIPES.items():
        path = directory / f"{name}.wav"
        if not path.exists():
            write_wav(path, render_recipe(recipe))
        paths[name] = path
    return paths


class SoundPlayer:
    """Plays the app's sounds honouring the user's preferences."""

    def __init__(self, settings, cache_dir=None, base_dir=None):
        self.settings = settings
        base = Path(base_dir) if base_dir else Path(__file__).resolve().parent.parent
        self.cache_dir = Path(cache_dir) if cache_dir else base / "data" / "sound_cache"
        self.paths = ensure_sounds()
        self._scaled_cache = {}

    def _scaled_path(self, name, volume_percent):
        key = (name, volume_percent)
        if key in self._scaled_cache:
            return self._scaled_cache[key]
        samples = render_recipe(RECIPES[name], volume=volume_percent / 100.0)
        path = write_wav(self.cache_dir / f"{name}_{volume_percent}.wav", samples)
        self._scaled_cache[key] = path
        return path

    def play(self, name):
        """Play a sound by name. Returns True if a sound was played."""
        if name not in RECIPES:
            return False
        if not self.settings.get("sound_enabled"):
            return False
        volume = self.settings.get("volume")
        if volume <= 0:
            return False
        path = self.paths[name] if volume >= 100 else self._scaled_path(name, volume)
        try:
            import winsound

            winsound.PlaySound(str(path),
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
            return True
        except Exception:
            return False  # non-Windows fallback is handled by the GUI (bell)

    def preview(self, name="focus_complete"):
        return self.play(name)
