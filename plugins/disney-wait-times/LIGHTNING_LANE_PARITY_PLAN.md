# Theme Park Wait Times: LightningLane-Live-LED parity plan

Status: planning only; current Disney Wait Times v0.2.0 remains unchanged.

## Reference
- Upstream: https://github.com/jc214809/LightningLane-Live-LED
- User fork: https://github.com/mcangeli/LightningLane-Live-LED
- Existing ULS native plugin: `plugins/disney-wait-times`

## Scope
Keep ULS's native 64x32 renderer, plugin settings, and idle rotation. Mirror the useful functionality and appearance of LightningLane-Live-LED rather than importing its standalone RGB matrix service.

1. **Park selection**: configurable multiple parks, not only Walt Disney World; use ThemeParks Wiki destination/park IDs and user-friendly names. Preserve current settings during migration.
2. **Attraction screens**: park header, attraction name with legible wrapping/scrolling, standby wait, open/closed/down status, configurable sort/filter, and character meet-and-greet wait times when available.
3. **Update modes**: retain bounded REST polling and offline last-good cache. Add optional ThemeParks Wiki API-key WebSocket live updates if the current API contract permits; initial REST snapshot and reconnect resync, bounded retry/backoff. No network work in frame renderer.
4. **Trip countdown**: multiple configured trip dates, park/destination label, days remaining, optional screen rotation.
5. **Weather**: optional park weather screen using an explicitly configured weather source; avoid duplicating ULS global weather unless independently enabled.
6. **64x32 visual parity**: adapt LightningLane layouts for the native 64x32 framebuffer, prioritize readability, status colors and park branding. No dependency on RGBMatrixEmulator or direct hardware access.
7. **Security and reliability**: private API key storage/redaction, bounded data and image sizes, timeouts, rate-limit handling, cache age indicator, no credentials in diagnostics.
8. **Testing**: park discovery, multiple parks, statuses, meet-and-greets, sorting, live/reconnect/fallback, trip countdown/DST, layout clipping, offline display, upgrade from v0.2.0 and Pi 3/Pi 5.

## Release approach
- Phase 1: audit current ULS plugin code and upstream layout/data model; define configuration migration and 64x32 screen mockups.
- Phase 2: multi-park and attraction/character parity, regression tests.
- Phase 3: countdown and optional weather, regression tests.
- Phase 4: optional WebSocket streaming with secure key handling, reconnection tests.
- Phase 5: physical Pi acceptance and plugin catalog version bump.

External plugin work must not modify frozen ULS Core v0.9.0. Upstream features and provider access may change; confirm API and licensing before copying code or art.
