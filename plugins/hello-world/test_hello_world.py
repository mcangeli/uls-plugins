"""Run from the ULS repository root with Python's unittest discovery."""
import unittest
from universal_led.display import Framebuffer
from hello_world import HelloWorldScreen


class HelloWorldTests(unittest.TestCase):
    def test_frame_dimensions(self):
        frame = HelloWorldScreen().render()
        self.assertIsInstance(frame, Framebuffer)
        self.assertEqual((frame.width, frame.height), (64, 32))

    def test_configure_changes_pixels(self):
        screen = HelloWorldScreen()
        default = screen.render().pixels
        screen.configure({"message": "WORLD"})
        self.assertNotEqual(screen.render().pixels, default)


if __name__ == "__main__":
    unittest.main()
