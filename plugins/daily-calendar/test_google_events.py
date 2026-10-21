"""Tests for Google Calendar API instance normalization, no credentials required."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("google_events", Path(__file__).with_name("google_events.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class GoogleEventsTests(unittest.TestCase):
    def test_recurring_instance_and_cancelled_exception(self):
        items = [
            {"id": "series_20261021T140000Z", "recurringEventId": "series",
             "summary": "Lesson", "start": {"dateTime": "2026-10-21T10:00:00-04:00"},
             "end": {"dateTime": "2026-10-21T11:00:00-04:00"}},
            {"status": "cancelled", "recurringEventId": "series",
             "start": {"dateTime": "2026-10-21T12:00:00-04:00"},
             "end": {"dateTime": "2026-10-21T13:00:00-04:00"}},
        ]
        result = module.normalize_instances(items)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Lesson")

    def test_all_day_exclusive_end(self):
        result = module.normalize_instances([{
            "summary": "Barn Day",
            "start": {"date": "2026-10-21"},
            "end": {"date": "2026-10-22"},
        }])
        self.assertTrue(result[0]["all_day"])
        self.assertEqual(result[0]["end"] - result[0]["start"], 86400)

    def test_dst_day_bounds(self):
        start, end = module.day_bounds(dt.date(2026, 11, 1), "America/New_York")
        duration = dt.datetime.fromisoformat(end) - dt.datetime.fromisoformat(start)
        self.assertEqual(duration.total_seconds(), 25 * 3600)

    def test_malformed_and_invalid_events_ignored(self):
        self.assertEqual(module.normalize_instances([{}, None, {
            "start": {"date": "2026-10-22"}, "end": {"date": "2026-10-21"}
        }]), [])


if __name__ == "__main__":
    unittest.main()
