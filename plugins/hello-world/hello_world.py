"""Small ULS native plugin: no external dependencies, no network calls.

ULS creates a fresh instance in a new subprocess for every frame.
configure() receives validated dashboard settings; render() returns a 64x32
Framebuffer. Do not print to stdout: ULS reserves it for raw RGB pixels.
"""
from universal_led.display import Framebuffer


class HelloWorldScreen:
    def __init__(self):
        self.message = "HELLO"

    def configure(self, settings):
        # ULS validates settings against settings-schema.json first.
        self.message = settings.get("message", "HELLO")

    def render(self):
        frame = Framebuffer(64, 32)
        # The built-in font is 5x7 with 6px spacing. Keep text within 64px.
        # Only glyphs present in universal_led.display.FONT are supported.
        message = self.message.upper()[:10]
        frame.text(message, 2, 12, (255, 200, 80))
        return frame
