"""Regression tests for recurring Google Calendar ICS events."""
import datetime as dt
import importlib.util
import sys
import types
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

if "universal_led.display" not in sys.modules:
    try:
        from universal_led.display import Framebuffer
    except ModuleNotFoundError:
        display = types.ModuleType("universal_led.display")
        display.Framebuffer = type("Framebuffer", (), {})
        package = types.ModuleType("universal_led")
        package.display = display
        sys.modules.setdefault("universal_led", package)
        sys.modules["universal_led.display"] = display

spec = importlib.util.spec_from_file_location("daily_calendar", Path(__file__).with_name("daily_calendar.py"))
calendar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(calendar)
ZONE = ZoneInfo("America/New_York")
NOW = dt.datetime(2026, 10, 22, 6, 43, tzinfo=ZONE).timestamp()


class RecurrenceTests(unittest.TestCase):
    def test_weekly_thursday_appointment(self):
        source = """BEGIN:VCALENDAR
BEGIN:VEVENT
UID:weekly
DTSTART;TZID=America/New_York:20261001T090000
DTEND;TZID=America/New_York:20261001T100000
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Weekly Lesson
END:VEVENT
END:VCALENDAR"""
        events = calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York")
        self.assertEqual([event["title"] for event in events], ["Weekly Lesson"])

    def test_exdate_removes_occurrence(self):
        source = """BEGIN:VEVENT
UID:weekly
DTSTART;TZID=America/New_York:20261001T090000
DTEND;TZID=America/New_York:20261001T100000
RRULE:FREQ=WEEKLY;BYDAY=TH
EXDATE;TZID=America/New_York:20261022T090000
SUMMARY:Weekly Lesson
END:VEVENT"""
        self.assertEqual(calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York"), [])

    def test_detached_rescheduled_instance(self):
        source = """BEGIN:VEVENT
UID:weekly
DTSTART;TZID=America/New_York:20261001T090000
DTEND;TZID=America/New_York:20261001T100000
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Original
END:VEVENT
BEGIN:VEVENT
UID:weekly
RECURRENCE-ID;TZID=America/New_York:20261022T090000
DTSTART;TZID=America/New_York:20261022T140000
DTEND;TZID=America/New_York:20261022T150000
SUMMARY:Rescheduled
END:VEVENT"""
        events = calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York")
        self.assertEqual([event["title"] for event in events], ["Rescheduled"])

    def test_all_day_recurring(self):
        source = """BEGIN:VEVENT
UID:all-day
DTSTART;VALUE=DATE:20261001
DTEND;VALUE=DATE:20261002
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:All Day
END:VEVENT"""
        events = calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York")
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["all_day"])


    def test_cancelled_detached_occurrence(self):
        source = """BEGIN:VEVENT
UID:weekly
DTSTART;TZID=America/New_York:20261001T090000
DTEND;TZID=America/New_York:20261001T100000
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Original
END:VEVENT
BEGIN:VEVENT
UID:weekly
RECURRENCE-ID;TZID=America/New_York:20261022T090000
DTSTART;TZID=America/New_York:20261022T090000
DTEND;TZID=America/New_York:20261022T100000
STATUS:CANCELLED
SUMMARY:Cancelled
END:VEVENT"""
        events = calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York")
        self.assertEqual(events, [])

    def test_long_running_weekly_series(self):
        source = """BEGIN:VEVENT
UID:old
DTSTART;TZID=America/New_York:20100107T090000
DTEND;TZID=America/New_York:20100107T100000
RRULE:FREQ=WEEKLY;BYDAY=TH
SUMMARY:Old Weekly
END:VEVENT"""
        events = calendar.active_today(calendar.parse_ics(source, now=NOW), NOW, "America/New_York")
        self.assertEqual([e["title"] for e in events], ["Old Weekly"])

if __name__ == "__main__":
    unittest.main()
