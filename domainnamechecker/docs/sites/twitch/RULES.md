# Twitch — handle rules (official)
Source: https://dev.twitch.tv/docs/api/ (Get Users; app token via client-credentials, no user permission needed)

## Acceptable names
- 4–25 chars, alphanumerics + underscore.

## Our method
- Keyed (`TWITCH_CLIENT_ID/SECRET`): Helix `users?login=` → exact login in data = TAKEN; healthy empty = NOT_FOUND (high).
- Unkeyed: content markers only (weak) → mostly UNKNOWN. Never trust size/status heuristics (proven: 200 both, 404-counts noise).
