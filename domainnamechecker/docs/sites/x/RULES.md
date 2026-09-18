# X — handle rules (official + observed)
Source: X help (handle change UI), X API v2 docs (get-user-by-username)

## Acceptable names
- 1–15 chars, letters/numbers/underscore only.

## Our method (no key → heuristic; keyed → definitive)
- Keyed: `GET /2/users/by/username/{u}` app Bearer → data match TAKEN, official Not Found → NOT_FOUND.
- Anonymous: profile URL 404 = free signal (high); 200 + `screen_name":"{u}` marker = taken (medium).
- 200 without marker / login wall → UNKNOWN. Syndication endpoints excluded (repeatedly break).
