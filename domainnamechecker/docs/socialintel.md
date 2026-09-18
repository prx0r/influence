# socialintel.md — namespace intelligence done honestly

Companion to `AVAILABILITY.md` (per-site methods). This file is the model:
states, evidence, and what we refuse to infer.

## The five states (shipping)

| State | Meaning | Emitted when |
|---|---|---|
| `TAKEN` | authoritative evidence the object exists | registry/API hit, exact canonical match |
| `AVAILABLE` | authoritative system says registrable | registrar check endpoint only (domains) |
| `NOT_FOUND` | no public object; claimability **unproved** | registry 404, oEmbed-missing, sparse-index miss |
| `RESERVED` | namespace explicitly holds it | (reserved for contract/registry holds; rarely observed) |
| `UNKNOWN` | auth/WAF/rate-limit/network/ambiguity | everything else — never a guess |

**The rule that matters:** `NOT_FOUND ≠ AVAILABLE`. PyPI's own docs prove names
can be unavailable with no visible project; TikTok holds released names;
registries reserve. Only a registration authority says AVAILABLE.

## Evidence attached to every verdict

`source` (authoritative-api | registry | onchain | public-catalog | html-heuristic),
`confidence`, `note` (the caveat, e.g. EMU blind spot), canonical match flag.
Network failures are never namespace semantics.

## Per-service verdicts (validated 2026-09-10, live both-directions)

- **Domains**: IANA bootstrap → RDAP JSON validation. TAKEN ~99.9%; 404 → UNREGISTERED (still check registrar to buy).
- **GitHub**: REST exists-check. EMU-hidden accounts also 404 → NOT_FOUND with note.
- **npm/PyPI**: registry lookup = package/project collision only (renamed adapters); 404 → NOT_FOUND + policy warning.
- **crates.io**: sparse index primary (no auth games), API fallback with identifying UA. 403 → UNKNOWN always.
- **YouTube**: Data API `forHandle` = excellent TAKEN; zero items → NO_ACTIVE_CHANNEL, not AVAILABLE.
- **TikTok**: oEmbed structural (`type==rich` + author_url match) = TAKEN; documented-missing → NOT_FOUND; else UNKNOWN.
- **ENS**: `ETHRegistrarController.available()` on-chain primary (configurable RPC); resolver fallback answers record-exists only.
- **App Store**: public-title collision intel, multi-storefront; never namespace proof.
- **Play**: package-ID namespace; title search = brand collision only.
- **X**: API v2 lookup if bearer present; else HTML heuristic fallback (404-free + screen_name marker).
- **Twitch**: Helix app-token (free); markers otherwise.
- **Reddit**: OAuth + `/user/about`; investigate `/api/username_available` next.
- **Instagram**: exact profile metadata only; never AVAILABLE anonymously.
- **LinkedIn**: UNKNOWN; authenticated UI is authority. No bypass attempts.

## Blind-adapter invariant (run before trusting any scraper)

KNOWN_TAKEN + RANDOM_VALID + target → if taken/random fingerprints match,
adapter is blind → UNKNOWN. This catches every IG-style wall automatically.

## Experiments log

- 2026-09-10: IG `302/0b` both ways → wall confirmed; Nitter 200s everything → rejected; TikTok oEmbed body shapes confirmed; crates sparse 200/404 clean; iTunes 429s under load → KV cache; GitHub EMU 404 accepted from docs; Reddit anon username_available → HTML wall; public RPCs 403 from our egress → on-chain deferred to configurable RPC.
