"""ULS Daily Calendar: dependency-free, text-only 64x32 ICS screen.

A short-lived render process never performs network I/O. A separate detached
refresh worker downloads the feed and atomically updates a private JSON cache.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from universal_led.display import Framebuffer

GOLD = (245, 195, 85)
WHITE = (235, 235, 230)
GREEN = (115, 225, 160)
DIM = (115, 135, 155)
MAX_FEED = 2 * 1024 * 1024


def unfold(source):
    lines = []
    for line in source.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if line.startswith((" ", "\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def decode_text(value):
    return (value.replace("\\n", " ").replace("\\N", " ")
            .replace("\\,", ",").replace("\\;", ";")
            .replace("\\\\", "\\"))


def parse_date(value, key, local_zone):
    value = value.strip()
    tzmatch = re.search(r"(?:^|;)TZID=([^;:]+)", key, re.I)
    if len(value) == 8 and value.isdigit():
        return dt.datetime.strptime(value, "%Y%m%d").replace(tzinfo=local_zone), True
    if value.endswith("Z"):
        parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    else:
        parsed = dt.datetime.strptime(value, "%Y%m%dT%H%M%S")
        zone = ZoneInfo(tzmatch.group(1)) if tzmatch else local_zone
        parsed = parsed.replace(tzinfo=zone)
    return parsed.astimezone(local_zone), False


WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _rule_values(value):
    return dict(part.split("=", 1) for part in value.split(";") if "=" in part)


def _event_fields(source):
    fields = None
    for line in unfold(source):
        if line == "BEGIN:VEVENT":
            fields = {}
        elif line == "END:VEVENT" and fields is not None:
            yield fields
            fields = None
        elif fields is not None and ":" in line:
            key, value = line.split(":", 1)
            fields.setdefault(key.split(";", 1)[0].upper(), []).append((key, value))


def _first(fields, name):
    return fields.get(name, [None])[0]


def _occurrences(start, rule, zone, window_start, window_end):
    """Bound recurrence expansion to a short window, without external dependencies."""
    parts = _rule_values(rule)
    freq = parts.get("FREQ", "")
    if freq not in ("DAILY", "WEEKLY", "MONTHLY", "YEARLY"):
        return
    interval = max(1, int(parts.get("INTERVAL", "1")))
    count = int(parts.get("COUNT", "0"))
    until = parts.get("UNTIL")
    until_time = parse_date(until, "UNTIL", zone)[0] if until else None
    byday = [WEEKDAYS[token[-2:]] for token in parts.get("BYDAY", "").split(",")
             if token[-2:] in WEEKDAYS and (len(token) == 2)]
    bymonthday = [int(n) for n in parts.get("BYMONTHDAY", "").split(",") if n]
    bymonth = [int(n) for n in parts.get("BYMONTH", "").split(",") if n]
    cursor = start.date()
    last = window_end.date()
    emitted = 0
    scanned = 0
    while cursor <= last and scanned < 366 * 100:
        scanned += 1
        day_delta = (cursor - start.date()).days
        week_delta = (cursor - start.date()).days // 7
        month_delta = (cursor.year - start.year) * 12 + cursor.month - start.month
        year_delta = cursor.year - start.year
        if freq == "DAILY":
            match = day_delta % interval == 0
        elif freq == "WEEKLY":
            match = week_delta % interval == 0 and cursor.weekday() in (byday or [start.weekday()])
        elif freq == "MONTHLY":
            match = month_delta % interval == 0 and cursor.day in (bymonthday or [start.day])
        else:
            match = year_delta % interval == 0 and cursor.month in (bymonth or [start.month]) and cursor.day in (bymonthday or [start.day])
        if bymonth and cursor.month not in bymonth:
            match = False
        if bymonthday and cursor.day not in bymonthday:
            match = False
        if byday and cursor.weekday() not in byday:
            match = False
        candidate = dt.datetime.combine(cursor, start.timetz())
        if until_time is not None and candidate > until_time:
            break
        if match and candidate >= start:
            emitted += 1
            if count and emitted > count:
                break
            if candidate >= window_start:
                yield candidate
        cursor += dt.timedelta(days=1)


def parse_ics(source, timezone="America/New_York", now=None):
    """Expand common ICS recurrences, exclusions and detached instances for the display window."""
    zone = ZoneInfo(timezone)
    now_dt = dt.datetime.fromtimestamp(time.time() if now is None else now, zone)
    window_start = now_dt - dt.timedelta(days=2)
    window_end = now_dt + dt.timedelta(days=35)
    events = []
    exclusions = {}
    detached = set()
    records = list(_event_fields(source))
    for fields in records:
        uid = (_first(fields, "UID") or ("", ""))[1]
        recurrence = _first(fields, "RECURRENCE-ID")
        if recurrence:
            try:
                original = parse_date(recurrence[1], recurrence[0], zone)[0]
                detached.add((uid, original.timestamp()))
            except (ValueError, OverflowError, KeyError):
                pass
        excluded = exclusions.setdefault(uid, set())
        for key, value in fields.get("EXDATE", []):
            for date_value in value.split(","):
                try:
                    excluded.add(parse_date(date_value, key, zone)[0].timestamp())
                except (ValueError, OverflowError):
                    pass
    for fields in records:
        try:
            if (_first(fields, "STATUS") or ("", ""))[1].upper() == "CANCELLED":
                continue
            start_key, start_val = _first(fields, "DTSTART")
            start, all_day = parse_date(start_val, start_key, zone)
            end_field = _first(fields, "DTEND")
            end = parse_date(end_field[1], end_field[0], zone)[0] if end_field else start + (dt.timedelta(days=1) if all_day else dt.timedelta(hours=1))
            if end <= start:
                continue
            duration = end - start
            uid = (_first(fields, "UID") or ("", ""))[1]
            title = decode_text((_first(fields, "SUMMARY") or ("", "UNTITLED"))[1]) or "UNTITLED"
            rule = _first(fields, "RRULE")
            starts = _occurrences(start, rule[1], zone, window_start - duration, window_end) if rule else [start]
            for occurrence in starts:
                if rule and (uid, occurrence.timestamp()) in detached:
                    continue
                if occurrence.timestamp() in exclusions.get(uid, set()):
                    continue
                finish = occurrence + duration
                if finish >= window_start and occurrence <= window_end:
                    events.append({"start": occurrence.timestamp(), "end": finish.timestamp(),
                                   "title": title, "all_day": all_day})
        except (KeyError, ValueError, OverflowError, TypeError):
            continue
    return sorted(events, key=lambda e: (e["start"], e["title"]))


def active_today(events, now, timezone):
    zone = ZoneInfo(timezone)
    today = dt.datetime.fromtimestamp(now, zone).date()
    selected = []
    for event in events:
        start = dt.datetime.fromtimestamp(event["start"], zone)
        end = dt.datetime.fromtimestamp(event["end"], zone)
        if end.timestamp() > now and start.date() <= today and (end - dt.timedelta(microseconds=1)).date() >= today:
            selected.append(event)
    return selected


def cache_path(feed_url):
    digest = hashlib.sha256(feed_url.encode("utf-8")).hexdigest()[:24]
    directory = Path(os.environ.get("ULS_CALENDAR_CACHE_DIR", "/var/lib/uls/plugin-cache/daily-calendar"))
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory / (digest + ".json")


def valid_url(url):
    parts = urlsplit(url)
    return (parts.scheme == "https" and bool(parts.hostname)
            and not parts.username and not parts.password and not parts.fragment)


def refresh_worker(path, timezone, refresh_minutes):
    """URL arrives on stdin, never on process command line or in cache."""
    url = sys.stdin.readline().rstrip("\n")
    if not valid_url(url):
        return
    try:
        req = Request(url, headers={"User-Agent": "ULS-Daily-Calendar/0.1"})
        with urlopen(req, timeout=8) as response:
            data = response.read(MAX_FEED + 1)
        if len(data) > MAX_FEED:
            raise ValueError("ICS feed too large")
        events = parse_ics(data.decode("utf-8-sig"), timezone)
        payload = {"fetched": time.time(), "events": events}
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".refresh-", delete=False) as handle:
            tmp = Path(handle.name)
            json.dump(payload, handle)
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except (OSError, ValueError, UnicodeError):
        # Keep last good cache; retry on the next refresh window.
        pass
    finally:
        lock = path.with_suffix(".lock")
        try:
            lock.unlink()
        except OSError:
            pass


def launch_refresh(url, path, timezone, refresh_minutes):
    lock = path.with_suffix(".lock")
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    except FileExistsError:
        try:
            if time.time() - lock.stat().st_mtime < 30:
                return
            lock.unlink()
        except OSError:
            return
        return
    try:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--refresh",
                                  str(path), timezone, str(refresh_minutes)],
                                 stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
        child.stdin.write((url + "\n").encode("utf-8"))
        child.stdin.close()
    except OSError:
        try:
            lock.unlink()
        except OSError:
            pass


def ascii_label(value):
    return "".join(c if c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 '" else " "
                   for c in value.upper()).strip() or "EVENT"


class DailyCalendarScreen:
    name = "daily-calendar"

    def __init__(self):
        self.feed_url = ""
        self.timezone = "America/New_York"
        self.refresh_minutes = 15
        self.event_seconds = 6

    def configure(self, settings):
        self.feed_url = str(settings.get("feed_url", "")).strip()
        self.timezone = str(settings.get("timezone", "America/New_York"))
        ZoneInfo(self.timezone)
        self.refresh_minutes = max(5, min(120, int(settings.get("refresh_minutes", 15))))
        self.event_seconds = max(2, min(60, int(settings.get("event_seconds", 6))))

    def render(self):
        frame = Framebuffer(64, 32)
        frame.text("TODAY", 1, 1, GOLD)
        for x in range(64):
            frame.pixel(x, 9, DIM)
        if not self.feed_url or not valid_url(self.feed_url):
            frame.text("SET ICS URL", 1, 15, DIM)
            return frame
        try:
            path = cache_path(self.feed_url)
            payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
            now = time.time()
            if now - payload.get("fetched", 0) >= self.refresh_minutes * 60:
                launch_refresh(self.feed_url, path, self.timezone, self.refresh_minutes)
            events = active_today(payload.get("events", []), now, self.timezone)
        except (OSError, ValueError, TypeError, KeyError):
            events = []
            now = time.time()
        if not events:
            frame.text("NO EVENTS", 1, 15, WHITE)
            return frame
        index = int(now // self.event_seconds) % len(events)
        event = events[index]
        title = ascii_label(event["title"])
        # Marquee on the 10-character-wide matrix text row.
        offset = int(now // 1.0) % (len(title) + 4) if len(title) > 10 else 0
        marquee = (title + "    " + title)[offset:offset + 10] if len(title) > 10 else title[:10]
        frame.text(marquee, 1, 12, WHITE)
        if event["all_day"]:
            label = "ALL DAY"
        else:
            when = dt.datetime.fromtimestamp(event["start"], ZoneInfo(self.timezone))
            label = when.strftime("%I:%M%p").lstrip("0")
        frame.text(ascii_label(label)[:10], 1, 23, GREEN)
        return frame


if __name__ == "__main__" and len(sys.argv) == 5 and sys.argv[1] == "--refresh":
    refresh_worker(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]))
