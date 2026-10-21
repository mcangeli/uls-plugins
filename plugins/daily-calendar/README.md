# Daily Calendar (native ULS text-only plugin)

Shows today's remaining events on a **64×32** matrix using ULS's built-in 5×7 pixel text font. **No image files, Pillow, Google login, OAuth, or third-party Python packages.** The returned `Framebuffer` is still the required 64×32 RGB pixel output; "text-only" means the plugin draws text directly.

## Install

Open **Plugin Manager → Install from GitHub**, and review:

`https://github.com/mcangeli/uls-plugins/tree/main/plugins/daily-calendar`

Install, enable, then open Settings. Set **Google Calendar ICS URL**, **IANA time zone** (default `America/New_York`), **Refresh every** (15 minutes), **Seconds per event** (6), and **Display duration** (12 seconds).

In Google Calendar, open **Settings → Settings for my calendars → Integrate calendar** and copy either the public iCal URL (only for public calendars) or **Secret address in iCal format** (for private calendars). Do **not** use the browser's calendar URL. Treat the secret address as a password: anyone holding it can read your calendar. ULS stores plugin settings locally and may expose the URL to authorized dashboard administrators; avoid sharing screenshots of the settings field.

## Behavior

- Shows events in start-time order, rotating one event every configured number of seconds.
- Events remain visible until their **end** time, then disappear immediately based on the local clock (even before the next feed refresh).
- Today's all-day and ongoing events remain visible until their end.
- When none remain, shows **NO EVENTS**. When unconfigured, shows **SET ICS URL**.
- Event titles scroll across the 10-character-wide text row; unsupported font characters are converted to spaces.
- The render process reads a private local JSON cache. If stale, it launches a separate short-lived fetch worker and immediately returns the current cached screen. The first display may say NO EVENTS until the first fetch completes. Cache contains event titles and times but **never the feed URL**. Refresh is at most every 15 minutes by default.
- Network failure retains the last successful cache. Clock and configured time zone determine event expiry.
- ULS live-game precedence can suppress plugin screens.

## Important v0.1.0 limitations

- **Recurring series with RRULE are not expanded**; those VEVENT entries are omitted. Single events and detached occurrences without RRULE work. A full recurrence parser is a planned follow-up.
- The plugin supports HTTPS ICS feeds. It does not authenticate with Google or store Google account credentials.
- A writable `/var/lib/uls/plugin-cache/daily-calendar` is required for the `uls` service account. If unavailable, set `ULS_CALENDAR_CACHE_DIR` to a writable private directory.
- The URL is passed to the refresh child over stdin, not on the command line; private URLs must still be protected in ULS settings.
- The first fetch runs asynchronously; it can take a few seconds. Feed downloads are limited to 2 MiB and 8 seconds.

## Example of a text-only screen

```python
from universal_led.display import Framebuffer
frame = Framebuffer(64, 32)
frame.text("NO EVENTS", 1, 15, (235, 235, 230))
return frame
```

No PNG or bitmap generation is necessary: ULS serializes the framebuffer to the LED matrix.
