"""Offline transport tests for the Google Calendar API client."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

directory = Path(__file__).parent
sys.path.insert(0, str(directory))
spec = importlib.util.spec_from_file_location("google_api", directory / "google_api.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


class Response:
    def __init__(self, data):
        self.data = json.dumps(data).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


class GoogleAPITests(unittest.TestCase):
    def test_calendar_list_pagination_and_auth(self):
        requests = []

        def opener(req, timeout):
            requests.append(req)
            q = parse_qs(urlsplit(req.full_url).query)
            if "pageToken" in q:
                return Response({"items": [{"id": "second", "summary": "Barn"}]})
            return Response({"items": [{"id": "primary", "primary": True}],
                             "nextPageToken": "next"})

        result = api.list_calendars("private-token", opener)
        self.assertEqual([c["id"] for c in result], ["primary", "second"])
        self.assertEqual(requests[0].get_header("Authorization"), "Bearer private-token")
        self.assertNotIn("private-token", requests[0].full_url)

    def test_recurring_instances_and_cancellation(self):
        def opener(req, timeout):
            query = parse_qs(urlsplit(req.full_url).query)
            self.assertEqual(query["singleEvents"], ["true"])
            self.assertEqual(query["showDeleted"], ["false"])
            return Response({"items": [
                {"summary": "Weekly lesson", "recurringEventId": "series",
                 "start": {"dateTime": "2026-10-21T10:00:00-04:00"},
                 "end": {"dateTime": "2026-10-21T11:00:00-04:00"}},
                {"status": "cancelled", "summary": "Cancelled",
                 "start": {"date": "2026-10-21"}, "end": {"date": "2026-10-22"}},
            ]})

        import datetime as dt
        result = api.fetch_today("token", ["barn@example.com"], day=dt.date(2026, 10, 21), opener=opener)
        self.assertEqual([e["title"] for e in result], ["Weekly lesson"])

    def test_repeated_page_token_rejected(self):
        def opener(req, timeout):
            return Response({"items": [], "nextPageToken": "loop"})

        with self.assertRaises(api.CalendarAPIError):
            api.list_calendars("token", opener)

    def test_missing_token_rejected(self):
        with self.assertRaises(api.CalendarAPIError):
            api.list_calendars("")


if __name__ == "__main__":
    unittest.main()
