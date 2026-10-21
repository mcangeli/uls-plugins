"""Read-only Google Calendar API transport and normalization.

This module does not store tokens or perform OAuth callbacks. Callers supply
a short-lived access token from a protected credential manager.
"""
from __future__ import annotations

import datetime as dt
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from google_events import day_bounds, normalize_instances

BASE = "https://www.googleapis.com/calendar/v3"
MAX_RESPONSE = 2 * 1024 * 1024
MAX_PAGES = 20


class CalendarAPIError(Exception):
    pass


def _get(path, access_token, params=None, opener=urlopen):
    if not isinstance(access_token, str) or not access_token.strip():
        raise CalendarAPIError("Google Calendar connection required")
    url = BASE + path + ("?" + urlencode(params) if params else "")
    request = Request(url, headers={
        "Authorization": "Bearer " + access_token,
        "Accept": "application/json",
        "User-Agent": "ULS-Daily-Calendar/0.2",
    })
    try:
        with opener(request, timeout=8) as response:
            raw = response.read(MAX_RESPONSE + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        # Do not include exception strings: some transports echo URLs/headers.
        raise CalendarAPIError("Google Calendar API request failed") from None
    if len(raw) > MAX_RESPONSE:
        raise CalendarAPIError("Google Calendar API response too large")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise CalendarAPIError("Invalid Google Calendar API response") from None
    if not isinstance(value, dict):
        raise CalendarAPIError("Invalid Google Calendar API response")
    return value


def _pages(path, access_token, params, opener=urlopen):
    token = None
    seen = set()
    for _ in range(MAX_PAGES):
        query = dict(params)
        if token:
            query["pageToken"] = token
        page = _get(path, access_token, query, opener=opener)
        items = page.get("items", [])
        if not isinstance(items, list):
            raise CalendarAPIError("Invalid Google Calendar API items")
        yield items
        token = page.get("nextPageToken")
        if not token:
            return
        if not isinstance(token, str) or token in seen:
            raise CalendarAPIError("Invalid Google Calendar pagination")
        seen.add(token)
    raise CalendarAPIError("Google Calendar pagination limit exceeded")


def list_calendars(access_token, opener=urlopen):
    calendars = []
    for items in _pages("/users/me/calendarList", access_token, {"maxResults": 250}, opener):
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                calendars.append({"id": str(item["id"]),
                                  "name": str(item.get("summary") or item["id"]),
                                  "primary": bool(item.get("primary"))})
    return calendars


def fetch_today(access_token, calendar_ids, timezone="America/New_York",
                day=None, opener=urlopen):
    if not isinstance(calendar_ids, (list, tuple)) or not calendar_ids:
        return []
    from zoneinfo import ZoneInfo
    day = day or dt.datetime.now(ZoneInfo(timezone)).date()
    start, end = day_bounds(day, timezone)
    events = []
    for calendar_id in calendar_ids:
        if not isinstance(calendar_id, str) or not calendar_id:
            raise CalendarAPIError("Invalid calendar ID")
        from urllib.parse import quote
        path = "/calendars/" + quote(calendar_id, safe="") + "/events"
        params = {"singleEvents": "true", "orderBy": "startTime",
                  "timeMin": start, "timeMax": end, "maxResults": 250,
                  "showDeleted": "false"}
        for items in _pages(path, access_token, params, opener):
            events.extend(normalize_instances(items, timezone))
    return sorted(events, key=lambda item: (item["start"], item["title"]))
