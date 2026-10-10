# Social onboarding registry

**Schema:** `influence.social_onboarding.v1`  
**File:** `data/social_onboarding.v1.json`  
**Code:** `core/cmail/social_onboarding.py`

Any brand gets the same objective claim kit. Agents and humans read the same registry — no per-brand wikis.

## Surfaces

| Surface | How |
|---------|-----|
| **Passport** | `influencer_passport()` emits `claim-*` static resources with kit metadata |
| **Dash rail** | Claim tasks → ▶ start guide card (steps + bio + pin + phone) |
| **Dash API** | `GET /api/onboarding?slug=oddhobb` or `?handle=…&domain=…` |
| **Chat** | `onboarding [slug]` · `socials` (list platforms) |
| **MCP** | `social.onboarding` · `social.platforms` |
| **Connector** | `SocialConnector` uses `desired.kit` for human instructions when present |

## Brand parameters

```
handle, domain, display_name, email, phone, website
bio_primary, bio_short, bio_x, bio_youtube   (optional overrides)
```

Defaults resolve from `data/social_onboarding.v1.json` → `defaults` (`{{handle}}`, `{{domain}}`, …).

## Claim order (registry)

`tiktok → youtube → x → instagram → pinterest` (+ optional `github`)

Priorities (dash urgency): TikTok 80 · YouTube 78 · X 76 · IG 70 · Pinterest 60.

## Commands

```bash
# List platforms
# (dash chat) socials

# Full kit for a brand
# (dash chat) onboarding oddhobb
# (MCP) social.onboarding {"slug":"oddhobb"}

# HTTP
curl 'http://127.0.0.1:8793/api/onboarding?slug=oddhobb'
```

## Extending

1. Edit `data/social_onboarding.v1.json` (add platform or change steps).
2. No code change required for new brands — pass different handle/domain.
3. New platform: add under `platforms` + optionally `claim_order`.
4. Tests: `core/cmail/test_social_onboarding.py`, `core/cmail/test_influencer.py`.

## Rules (unchanged)

- Human performs every signup (ToS/CAPTCHA). Kit is instructions only.
- Publish stays `human_confirm` until QP receipts exist.
- Never invent a fallback handle — screenshot + report.
- Secrets never in kit output; OTPs read from phone edge.
