"""Normalize Google Calendar API event instances for the ULS 64x32 calendar cache.

Pure transformation only. Authorization and API transport are separate work.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo


def _parse_boundary(value, zone):
    if "date" in value:
        day = dt.date.fromisoformat(value["date"])
        return dt.datetime.combine(day, dt.time.min, zone), True
    raw = value["dateTime"].replace("Z", "+00:00")
    parsed = dt.datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(value.get("timeZone") or str(zone)))
    return parsed.astimezone(zone), False


def normalize_instances(items, timezone="America/New_York"):
    """Convert instances.list / events.list(singleEvents=true) into cache events.

    Google expands recurring masters with singleEvents=true. Cancelled
    instances are excluded; the API query must bound timeMin/timeMax.
    """
    zone = ZoneInfo(timezone)
    result = []
    for item in items:
        if not isinstance(item, dict) or item.get("status") == "cancelled":
            continue
        try:
            start, all_day = _parse_boundary(item["start"], zone)
            end, _ = _parse_boundary(item["end"], zone)
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if end <= start:
            continue
        result.append({
            "start": start.timestamp(),
            "end": end.timestamp(),
            "title": str(item.get("summary") or "UNTITLED"),
            "all_day": all_day,
        })
    return sorted(result, key=lambda e: (e["start"], e["title"]))


def day_bounds(day, timezone):
    """UTC query bounds for one local calendar day, including DST changes."""
    zone = ZoneInfo(timezone)
    start = dt.datetime.combine(day, dt.time.min, zone)
    end = dt.datetime.combine(day + dt.timedelta(days=1), dt.time.min, zone)
    return (start.astimezone(dt.timezone.utc).isoformat(),
            end.astimezone(dt.timezone.utc).isoformat())
