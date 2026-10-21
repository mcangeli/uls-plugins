"""Small dependency-free 64x32 animated fish screen."""
import time
from universal_led.display import Framebuffer

WATER = (0, 12, 38)
FISH = (255, 170, 38)
FIN = (245, 102, 35)
EYE = (8, 15, 28)
BUBBLE = (67, 177, 226)


class SwimmingFishScreen:
    name = "swimming-fish"

    def __init__(self, clock=None):
        self.clock = clock or time.monotonic

    def render(self) -> Framebuffer:
        frame = Framebuffer(64, 32)
        for y in range(32):
            for x in range(64):
                frame.pixel(x, y, WATER)
        tick = int(self.clock() * 5)
        cx = (tick % 86) - 11
        cy = 15 + ((tick // 7) % 5) - 2
        # Body: rounded silhouette, pointed snout at the right.
        rows = { -4: (0, 3), -3: (-4, 6), -2: (-6, 8),
                 -1: (-7, 9), 0: (-7, 10), 1: (-7, 9),
                 2: (-6, 8), 3: (-4, 6), 4: (0, 3) }
        for dy, (left, right) in rows.items():
            for dx in range(left, right + 1):
                frame.pixel(cx + dx, cy + dy, FISH)
        # Tail flaps every other frame.
        tail_offset = 2 if tick % 2 else -2
        for dx in range(-12, -7):
            spread = -dx - 7
            for dy in range(-spread, spread + 1):
                if abs(dy - tail_offset) <= spread:
                    frame.pixel(cx + dx, cy + dy, FIN)
        for dx in range(-2, 3):
            frame.pixel(cx + dx, cy - 5, FIN)
            frame.pixel(cx + dx, cy + 5, FIN)
        frame.pixel(cx + 6, cy - 2, EYE)
        # Bubbles rise on independent cycles.
        for i in range(4):
            bx = 9 + i * 16 + (i % 2) * 3
            by = 31 - ((tick * (i % 2 + 1) + i * 9) % 37)
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                frame.pixel(bx + dx, by + dy, BUBBLE)
        return frame
