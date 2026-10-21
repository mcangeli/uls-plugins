"""Standalone tests for the Swimming Fish plugin's settings contract."""
import importlib.util
import unittest
from pathlib import Path

MODULE = Path(__file__).with_name("swimming_fish.py")


def load_screen():
    spec = importlib.util.spec_from_file_location("swimming_fish_tested", MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SwimmingFishSettingsTests(unittest.TestCase):
    def test_palette_selection_changes_rendered_pixels(self):
        module = load_screen()
        colors = {}
        for color in ("gold", "blue", "pink"):
            screen = module.SwimmingFishScreen(clock=lambda: 4.0)
            screen.configure({"fish_color": color, "animation_speed": 1})
            frame = screen.render()
            colors[color] = {pixel for row in frame.pixels for pixel in row}
        self.assertIn(module.FISH, colors["gold"])
        self.assertIn((62, 167, 255), colors["blue"])
        self.assertIn((255, 128, 190), colors["pink"])

    def test_speed_changes_animation_position(self):
        module = load_screen()
        slow = module.SwimmingFishScreen(clock=lambda: 4.0)
        fast = module.SwimmingFishScreen(clock=lambda: 4.0)
        slow.configure({"animation_speed": 0.25, "fish_color": "gold"})
        fast.configure({"animation_speed": 3, "fish_color": "gold"})
        self.assertNotEqual(slow.render().pixels, fast.render().pixels)

    def test_defaults_remain_backward_compatible(self):
        module = load_screen()
        old = module.SwimmingFishScreen(clock=lambda: 4.0)
        new = module.SwimmingFishScreen(clock=lambda: 4.0)
        new.configure({})
        self.assertEqual(old.render().pixels, new.render().pixels)


if __name__ == "__main__":
    unittest.main()
