"""Dependency-free ThemeParks Wiki REST wait-time screen for ULS."""
import json
import time
from urllib.request import Request, urlopen
from universal_led.display import Framebuffer

PARKS = {
    "Magic Kingdom": "75ea578a-adc8-4116-a54d-dccb60765ef9",
    "EPCOT": "47f90d2c-e191-4239-a466-5892ef59a88b",
    "Hollywood Studios": "288b6a4b-74b3-4f67-9a2a-7b0fda2bfa9b",
    "Animal Kingdom": "1c84a229-8862-4648-9c71-378ddd2c7693",
}
LABELS = {"Magic Kingdom": "MAGIC KINGDOM", "EPCOT": "EPCOT",
          "Hollywood Studios": "HOLLYWOOD", "Animal Kingdom": "ANIMAL KINGDOM"}
WHITE = (230, 235, 240)
GOLD = (255, 190, 65)
GREEN = (100, 220, 145)
DIM = (100, 120, 145)

def parse_live(payload, max_wait=180):
    """Only open attractions with a numeric standby wait; ignore paid queue estimates."""
    rows = []
    for entity in payload.get("liveData", []):
        if not isinstance(entity, dict) or entity.get("entityType") != "ATTRACTION":
            continue
        if entity.get("status") != "OPERATING":
            continue
        standby = (entity.get("queue") or {}).get("STANDBY") or {}
        wait = standby.get("waitTime")
        if isinstance(wait, bool) or not isinstance(wait, int) or wait < 0:
            continue
        if max_wait and wait > max_wait:
            continue
        name = entity.get("name")
        if isinstance(name, str) and name.strip():
            rows.append((name.strip(), wait))
    return sorted(rows, key=lambda item: (item[1], item[0]))

class DisneyWaitTimesScreen:
    name = "disney-wait-times"

    def __init__(self, clock=None, fetch=None):
        self.clock = clock or time.monotonic
        self.fetch = fetch or self._fetch
        self.park = "Magic Kingdom"
        self.refresh_minutes = 5
        self.max_wait_minutes = 180
        self._updated = -float("inf")
        self._rows = []
        self._error = False

    def configure(self, settings):
        park = settings.get("park", "Magic Kingdom")
        self.park = park if park in PARKS else "Magic Kingdom"
        self.refresh_minutes = max(2, min(60, int(settings.get("refresh_minutes", 5))))
        self.max_wait_minutes = max(0, min(300, int(settings.get("max_wait_minutes", 180))))
        self._updated = -float("inf")

    @staticmethod
    def _fetch(park):
        url = "https://api.themeparks.wiki/v1/entity/" + PARKS[park] + "/live"
        request = Request(url, headers={"User-Agent": "ULS-Disney-Wait-Times/0.1"})
        with urlopen(request, timeout=4) as response:
            data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise ValueError("Theme park response too large")
        return json.loads(data)

    def render(self):
        now = self.clock()
        if now - self._updated >= self.refresh_minutes * 60:
            self._updated = now
            try:
                self._rows = parse_live(self.fetch(self.park), self.max_wait_minutes)
                self._error = False
            except (OSError, ValueError, KeyError, TypeError):
                self._error = True
        frame = Framebuffer(64, 32)
        frame.text(LABELS[self.park][:10], 1, 1, GOLD)
        if not self._rows:
            frame.text("NO LIVE WAITS" if not self._error else "DATA OFFLINE", 1, 13, DIM)
            return frame
        # Page through the sorted queue every six seconds.
        page = int(now // 6) % max(1, (len(self._rows) + 1) // 2)
        for i, (name, minutes) in enumerate(self._rows[page * 2:page * 2 + 2]):
            y = 11 + i * 10
            label = "".join(ch for ch in name.upper() if ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '")[:8]
            frame.text(label, 1, y, WHITE)
            frame.text(str(minutes).rjust(3), 45, y, GREEN)
        if self._error:
            frame.pixel(63, 0, (240, 80, 80))
        return frame
