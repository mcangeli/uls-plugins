# Daily Calendar: direct Google Calendar connection

Status: design specification, **not yet implemented**. The existing ICS source stays available and working. This is an external plugin release, independent of ULS Core 0.9.0.

## User experience

1. Choose **Calendar source: Google account** or **ICS URL** in plugin settings.
2. For Google, click **Connect Google Calendar** and complete Google's authorization in a browser. Never ask for the user's Google password.
3. Grant only `https://www.googleapis.com/auth/calendar.readonly`.
4. Select one or more calendars, set timezone and refresh interval, then save.
5. Show connection status, last successful sync, actionable errors, and **Disconnect** (revoke and delete tokens).
6. **Refresh calendar now** bypasses the local cache interval for either source; it cannot bypass upstream ICS publication delay.

## Authentication and security

- Use OAuth 2.0 authorization code flow with PKCE, unpredictable `state`, explicit redirect URI, and short-lived pending state.
- OAuth client configuration is supplied by the administrator or a separately managed authorized service. **Do not embed client secrets or refresh tokens in public plugin code or settings schemas.**
- The dashboard callback and token handling require an explicitly reviewed host integration surface. Do not create a generic unauthenticated callback or expose tokens through plugin settings APIs.
- Store refresh tokens in a service-owned private file (0600) outside exported portable backups by default. Document backup/migration policy and allow explicit disconnection.
- Scope credentials to the plugin and Google account; do not put tokens in logs, URLs, process arguments, screenshots, or error messages.
- Check Google OAuth app verification, publishing status, and consent-screen requirements before declaring the connection suitable for other users.

## Calendar API behavior

- Fetch calendar list using read-only credentials, then request events for the display's local day with `singleEvents=true`, `orderBy=startTime`, and a bounded `timeMin`/`timeMax`.
- Handle pagination, cancellations, all-day dates, timezone/DST boundaries, and recurring-event exceptions.
- Poll with a configurable interval (initial target 5 minutes), honor HTTP 429/5xx backoff, and keep last successful data when offline.
- Keep network I/O outside the 64x32 render subprocess; continue atomic JSON caching and local expiry filtering.
- Use the existing text framebuffer, display duration, and live-game preemption behavior.
- ICS remains a supported fallback; Google API is the recommended source when quick updates matter.

## Acceptance tests

- Authorization: state/PKCE, callback rejection, token expiry/refresh, disconnect/revocation, permissions, and no credential leaks.
- Data: today's events, weekly recurring series, cancelled and moved occurrences, all-day events, DST, multiple calendars, pagination.
- Reliability: API errors, offline cached display, rate-limit backoff, manual refresh, Pi 3 and Pi 5.
- Compatibility: existing ICS settings and caches remain usable without Google credentials.

**Release boundary:** Do not merge a partial OAuth login into a production plugin. Deliver the complete connection, callback, token lifecycle, and tests together.
