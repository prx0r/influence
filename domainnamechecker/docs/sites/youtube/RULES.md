# YouTube — handle rules (official)
Source: https://developers.google.com/youtube/v3/docs/channels/list (forHandle, updated 2026-06-01)

## Acceptable names
- Handles unique per channel, 3–30 chars; change via Studio UI (claim authority).

## Our method
- Keyed (`YT_API_KEY` secret): `channels.list(forHandle=)` → 1 item = TAKEN (high); 0 items = NO_ACTIVE_CHANNEL (not AVAILABLE — holds/policies possible).
- Unkeyed: 404 on /@ = free signal; HTML markers fallback.
