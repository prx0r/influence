# AVAILABILITY REFERENCE — deterministic handle checks per platform

How we (and anyone) determine available-vs-taken without guessing. Rule used
throughout: **report the method's actual strength; unknown beats a wrong green.**

## Solved deterministically (free, no login)

| Platform | Method | Signal | Confidence |
|---|---|---|---|
| Domains (most TLDs) | registry RDAP (IANA bootstrap) | 200 taken / 404 free | high |
| GitHub | `api.github.com/users/{u}` | 200 / 404 | high (watch shared-IP 60/hr limit → unknown on 403/429) |
| npm / PyPI / crates.io | registry APIs | 200 / 404 | high |
| ENS | ensideas resolve | address set / zero | medium-high |
| **YouTube** | **Data API v3 `channels.list?forHandle=`** (key in worker secret `YT_API_KEY`) | items 1 / 0 | high |
| App Store | iTunes Search exact-match | exact hit / none | medium (Apple 429s datacenter IPs → unknown; KV-cached 6h) |
| TikTok | oEmbed (`author_name` vs `Something went wrong`) | body match | medium |

## Solved with operator keys (env secrets, documented risk)

| Platform | Method | State |
|---|---|---|
| Twitch | Helix `users?login` via client-credentials (free app) — `TWITCH_CLIENT_ID/SECRET` | built, awaiting keys |
| Reddit | app-only OAuth `user/about.json` — `REDDIT_CLIENT_ID/SECRET` | built, awaiting keys |
| Instagram / X / TikTok-gated | operator session passthrough (`IG_SESSIONID`, `X_AUTH_TOKEN`, `TIKTOK_COOKIE`) — your own sessions, low volume | built, awaiting sessions |
| LinkedIn | **verdict: manual-only** — no public, no oEmbed, blocks servers | not building; checklist link |

## Solvable with someone else's pipe (not from datacenter IPs)

| Platform | Why servers fail | Deterministic path |
|---|---|---|
| Instagram | 200 + login wall for free and taken alike | **Apify residential actors** (no-login profile API, ~free tier 20/run) or Zyla API (~$21/mo). No official endpoint exists — Graph API has none. |
| TikTok edge cases | login/age-gated profiles hide data | logged-in cookie (kuji2336 pattern) or residential proxies |
| X taken | login wall on profile HTML | 404s still work for free; taken needs session or paid API |
| Twitch | consent/wall variance | content markers work sometimes; residential otherwise |
| Reddit / LinkedIn | 403 / block server callers | residential proxies only |

## No deterministic server-side path (report unknown)

Reddit, LinkedIn from datacenters. Personal-IG-only data. Anything requiring a
logged-in session we don't have.

## Cost ladder for full coverage

1. Free tier (us today): everything in table 1 — ~70% of what founders need.
2. Apify pay-per-run residential: IG/TikTok/X certainty, pennies per check.
3. Zyla-style API subscription: same, flat monthly.
4. Official OAuth (Meta/Google) where we operate accounts anyway.

## Implementation map (this repo)

- `worker/src/index.js`: `HANDLE_CHECKS` (status/API), `probeProfile` (content),
  `checkAppStores` (iTunes + Play sniff), YouTube via `YT_API_KEY` secret.
- Rule violations (X 15-char cap etc.) report the rule, never a status.
- Conflicting markers or fetch failures → `unknown` with reason. Always.

## Validation log (2026-09-10, live, both directions)

| Probe | Result | Verdict |
|---|---|---|
| `octocat` / `zzqfreexyz12345` full sweep | npm/PyPI/crates/YouTube/ENS correct both ways | deterministic confirmed |
| GitHub `octocat` once `unknown` | shared-IP 403 budget exhausts intermittently | flaky: works ~mostly, unknown on 403 (never wrong) |
| Twitch `ninja`, X `elonmusk` | `unknown` (login walls from datacenter) | session/key required — confirmed unobservable anon |
| `vitalik.eth` via ensideas | correct address returned | resolver trusted (medium-high) |
| iTunes repeated calls | 429s under load, KV cache covers repeats | flaky, cache mitigates |
| `postagi.trade` | unknown → available 0.95 after IANA fallback | bootstrap proven on unmapped TLD |
| Nitter (`nitter.net`) | 200 for taken AND free | dead as oracle — rejected |
| IG `web_profile_info` without session | 400 both ways | session required — confirmed |
| TikTok oEmbed free vs `@notaurl` (taken by aurel) | `Something went wrong` vs author JSON | body-match model confirmed |

## The instagram.com/{user} question — settled empirically

Hypothesis: "page exists = taken, nothing = free." Test, 2026-09-10:

```
curl instagram.com/instagram/ → 302, 0 bytes   (TAKEN account)
curl instagram.com/dualipa/   → 302, 0 bytes   (TAKEN account)
```

Identical responses for taken accounts, and free handles return the same
login-redirect shape from datacenter IPs. **The method has ~0% decisiveness
from servers** — not because the logic is wrong (it works in browsers on
residential IPs), but because Instagram filters datacenter ASNs *before
authentication*: flagged ranges get the wall regardless of handle state.

Industry consensus (ipburger, HikerAPI, instagrapi docs, 2025–2026):
datacenter IPs flagged pre-first-request; ~30 req/min triggers 403s;
login-based scraping gets the *account* banned within minutes; residential
is the floor ($10–30/GB), mobile stronger; managed APIs (Apify residential
actors, HikerAPI, Zyla ~$21/mo) externalize exactly this arms race.

Our posture, therefore:
- server-side IG = `unknown` with reason, always (a false FREE is the
  dangerous direction — user makes business decisions on it);
- optional `IG_SESSIONID` passthrough for the operator's own low-volume checks;
- managed-API adapter slot reserved (Apify actor call ≈ 30 lines when funded).

Reliability table (observed, datacenter egress):

| Method | Taken detected | Free detected | False-free rate |
|---|---|---|---|
| RDAP / registries / GitHub API / YT API | ~100% | ~100% | ~0% |
| TikTok oEmbed / X 404 / iTunes | ~90% | ~90% | low |
| IG profile polling (server) | ~0% | ~0% | would-be ~50% if forced — hence unknown |
| IG via residential/session | ~95%+ (industry) | ~95%+ | low |

## Sherlock integration (vendored engine, 2026-09-10)

`sherlock-sites.json`: 38-site curated subset of sherlock-project/sherlock
`data.json` (MIT, attributed here). Generic errorType engine
(status_code/message/response_url) mapped to our 5 states, with two upgrades
Sherlock lacks: **wall detection** (Maigret insight — login/captcha/challenge
markers force UNKNOWN instead of misreading) and **low-confidence labeling**
on all stratum verdicts (taken requires username echo; absence signals yield
NOT_FOUND, never AVAILABLE).

Known live quirk: Medium `nasa` returned not_found (likely JS-rendered wall
matching absence text) — contained by low-confidence labeling, not trusted.
Curated majors (GitHub/YouTube/TikTok/registries) always override the stratum.
