"""Dependency-free Daily Calendar unit tests. Run from ULS checkout with PYTHONPATH set."""
import datetime as dt
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

PLUGIN = Path(__file__).with_name("daily_calendar.py")
spec = importlib.util.spec_from_file_location("daily_calendar", PLUGIN)
calendar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calendar)


class CalendarTests(unittest.TestCase):
    def test_ics_timed_all_day_and_cancelled(self):
        source = """BEGIN:VCALENDAR
BEGIN:VEVENT
DTSTART;TZID=America/New_York:20261021T100000
DTEND;TZID=America/New_York:20261021T110000
SUMMARY:Riding\\, Lesson
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20261021
DTEND;VALUE=DATE:20261022
SUMMARY:Barn Day
END:VEVENT
BEGIN:VEVENT
DTSTART:20261021T120000Z
DTEND:20261021T130000Z
STATUS:CANCELLED
END:VEVENT
END:VCALENDAR"""
        events = calendar.parse_ics(source)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["title"], "Barn Day")
        self.assertEqual(events[1]["title"], "Riding, Lesson")

    def test_event_expires_at_end_not_start(self):
        events = calendar.parse_ics("""BEGIN:VEVENT
DTSTART:20261021T100000Z
DTEND:20261021T110000Z
SUMMARY:Meeting
END:VEVENT""", "UTC")
        started = dt.datetime(2026, 10, 21, 10, 30, tzinfo=dt.timezone.utc).timestamp()
        ended = dt.datetime(2026, 10, 21, 11, 0, tzinfo=dt.timezone.utc).timestamp()
        self.assertEqual(len(calendar.active_today(events, started, "UTC")), 1)
        self.assertEqual(calendar.active_today(events, ended, "UTC"), [])

    def test_text_frame_is_64_by_32_and_no_network(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {"ULS_CALENDAR_CACHE_DIR": temp}):
            plugin = calendar.DailyCalendarScreen()
            frame = plugin.render()
            self.assertEqual((frame.width, frame.height), (64, 32))
            plugin.configure({"feed_url": ""})
            self.assertEqual((plugin.render().width, plugin.render().height), (64, 32))

    def test_reject_insecure_feed_url(self):
        self.assertFalse(calendar.valid_url("http://example.com/feed.ics"))
        self.assertFalse(calendar.valid_url("https://user:pass@example.com/feed.ics"))
        self.assertTrue(calendar.valid_url("https://calendar.google.com/calendar/ical/test/basic.ics"))


if __name__ == "__main__":
    unittest.main()
