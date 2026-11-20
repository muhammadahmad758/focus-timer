import tempfile
import unittest
import wave
from pathlib import Path

from focus_timer import sounds
from focus_timer.settings import AppSettings


class SettingsTests(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = AppSettings(Path(tmp) / "settings.json")
            self.assertTrue(s.get("sound_enabled"))
            self.assertEqual(s.get("volume"), 70)
            self.assertEqual(s.get("focus_minutes"), 25)
            self.assertEqual(s.get("long_break_minutes"), 15)

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            s = AppSettings(path)
            s.set("volume", 40)
            s.set("animations_enabled", False)
            again = AppSettings(path)
            self.assertEqual(again.get("volume"), 40)
            self.assertFalse(again.get("animations_enabled"))

    def test_bad_values_are_clamped_or_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = AppSettings(Path(tmp) / "settings.json")
            s.set("volume", 999)
            self.assertEqual(s.get("volume"), 100)
            s.set("focus_minutes", 0)
            self.assertEqual(s.get("focus_minutes"), 25)  # invalid -> default kept via clean
            s.set("sound_enabled", "yes")
            self.assertTrue(s.get("sound_enabled"))  # non-bool ignored

    def test_corrupt_settings_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("### not json", encoding="utf-8")
            s = AppSettings(path)
            self.assertEqual(s.get("volume"), 70)


class SoundTests(unittest.TestCase):
    def test_all_recipes_render_valid_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = sounds.ensure_sounds(Path(tmp))
            self.assertEqual(set(paths), set(sounds.RECIPES))
            for name, path in paths.items():
                with wave.open(str(path)) as wav:
                    self.assertEqual(wav.getnchannels(), 1)
                    self.assertEqual(wav.getframerate(), sounds.SAMPLE_RATE)
                    self.assertGreater(wav.getnframes(), 1000)

    def test_volume_scaling_reduces_amplitude(self):
        loud = sounds.render_recipe(sounds.RECIPES["focus_complete"], volume=1.0)
        quiet = sounds.render_recipe(sounds.RECIPES["focus_complete"], volume=0.25)
        self.assertAlmostEqual(max(quiet) / max(loud), 0.25, delta=0.02)

    def test_player_respects_disabled_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = AppSettings(Path(tmp) / "settings.json")
            s.set("sound_enabled", False)
            player = sounds.SoundPlayer(s, cache_dir=Path(tmp) / "cache",
                                        base_dir=Path(tmp))
            self.assertFalse(player.play("focus_complete"))
            self.assertFalse(player.play("not_a_sound"))


if __name__ == "__main__":
    unittest.main()
