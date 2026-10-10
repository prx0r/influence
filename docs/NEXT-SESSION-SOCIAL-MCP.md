# NEXT SESSION — Social posting MCP + secure credentials

**Owner ask (2026-10-06):** pi should have MCP tools to post to X / Instagram / TikTok / YouTube. Store usernames + secrets securely. Full login chain + validation email/SMB via brand phone. No paid Postiz SaaS; no Docker preference — use what we already built.

**Status now:** accounts exist; publisher adapters already written in `stevejobless/publisher/adapters/`; dash chat is operator-mimo with read-only tools; phone OTP live at `phone.agentcom.org`; dash open at `agentcom.org`.

---

## 0. What we already own (do not rebuild)

| Asset | Path |
|-------|------|
| X adapter (tweepy OAuth1) | `/root/stevejobless/stevejobless/publisher/adapters/twitter.py` |
| Instagram Graph adapter | `.../adapters/instagram.py` |
| TikTok Content Posting adapter | `.../adapters/tiktok.py` |
| YouTube Data API upload adapter | `.../adapters/youtube.py` |
| Brand phone OTP | `+44 7822 000802` · `https://phone.agentcom.org/app` |
| Brand email → cmail | `hello@oddhobb.com` (CF Email Routing → cmail worker) |
| Vault | `agent-vault` oracle vault |
| Dash operator chat | `influence/dash/agent_chat.py` (mimo + read-only MCP tools) |
| Dash | `https://agentcom.org` · Notifications + Agents bottom ledger |
| Social claim registry | `influence/data/social_onboarding.v1.json` |

---

## 1. Research summary (web, 2026-10)

### X (Twitter)
- **Pricing:** pay-per-use credits. Post **no URL = $0.015** · post **with URL = $0.20**. Not a £5/mo plan. 1 plain post/day ≈ **$0.45/mo**.
- **Auth for posting:** OAuth **1.0a User Context** (4 keys) — simplest for a single brand account on a VPS. Tokens do not expire until revoked. OAuth 2.0 PKCE also works but needs refresh (`offline.access`) + `media.write` for media.
- **Portal:** https://developer.x.com → Project → App → User auth OAuth 1.0a → **Read and Write** → **regenerate** access token after permission change.
- **Endpoint:** `POST https://api.x.com/2/tweets` body `{"text":"..."}`.
- **Media:** v2 `/2/media/upload` INIT→APPEND→FINALIZE or legacy v1.1 upload (OAuth1). Media IDs expire 24h.
- **Gotchas:** app must be attached to a **Project**; free tier closed Feb 2026; Bearer-only cannot post; URL in post body costs 13× — put links in bio/reply/image text.

**Vault keys to create:**
```
X_API_KEY
X_API_SECRET
X_ACCESS_TOKEN
X_ACCESS_TOKEN_SECRET
# optional read:
X_BEARER_TOKEN
```

### Instagram
- **API:** Graph API — **Business or Creator only** (personal cannot publish).
- **Two paths:**
  - Instagram Login → `graph.instagram.com` · perms `instagram_business_basic`, `instagram_business_content_publish` · **no FB Page required**
  - Facebook Login → `graph.facebook.com` · `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` · **Page required**
- **Own-account shortcut:** if app serves only your accounts, no full App Review — Standard Access as admin/developer/tester is enough. Advanced Access + Business Verification only needed to publish for *other* users.
- **Publish flow (two-step):** `POST /{ig-user-id}/media` (public `image_url`/`video_url` + caption) → poll `status_code` FINISHED → `POST /{ig-user-id}/media_publish?creation_id=...`.
- **Limits:** ~100 API posts / rolling 24h per account (docs conflict 50 vs 100 — query `content_publishing_limit`). Images JPEG, publicly fetchable URL.
- **Media hosting:** R2 public URL or oddhobb.com asset path — Meta cURLs the file.

**Vault keys:**
```
META_APP_ID / FACEBOOK_APP_ID
META_APP_SECRET / FACEBOOK_APP_SECRET
# own-account path:
IG_USER_ID
IG_ACCESS_TOKEN          # long-lived (60d) — refresh before expiry
# FB-login path extras:
FB_PAGE_ID
FB_PAGE_ACCESS_TOKEN
```

### TikTok
- **API:** Content Posting API — free to call; **app audit** gates public posts.
- **Until audit passes:** posts forced **SELF_ONLY** (private). Max ~5 posting users / 24h unaudited.
- **Scopes:** `video.publish` (direct) · `video.upload` (inbox draft) · plus `user.info.basic` etc.
- **Flow:** creator_info/query → `POST /v2/post/publish/video/init/` (or content/init for photos) with `PULL_FROM_URL` or `FILE_UPLOAD` → upload/pull → poll `/v2/post/publish/status/fetch/` until PUBLISH_COMPLETE.
- **Limits:** 6 req/min/user; upload_url expires 1h; domain ownership verification for PULL_FROM_URL.
- **Portal:** https://developers.tiktok.com → app → Login Kit + Content Posting (Direct Post on) → redirect URI → scopes → app review → Content Posting audit.

**Vault keys:**
```
TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET
TIKTOK_ACCESS_TOKEN      # after OAuth
TIKTOK_OPEN_ID
```

### YouTube
- **API:** Data API v3 `videos.insert` — free quota.
- **Auth:** OAuth 2.0 web flow · scope `https://www.googleapis.com/auth/youtube.upload` · **`access_type=offline`** for refresh token.
- **Gotchas:**
  - Refresh token only on **first** consent.
  - App in **Testing** → refresh tokens die in **7 days** → publish OAuth app or re-consent weekly.
  - Sensitive scope → Google OAuth verification + YouTube audit if you want non-private uploads for external users. Own channel + admin = can upload unlisted/public with test users.
- **Upload:** resumable POST `https://www.googleapis.com/upload/youtube/v3/videos`.

**Vault keys:**
```
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
YOUTUBE_CHANNEL_ID       # optional, for receipts
```

---

## 2. Secure credential storage (our pattern)

**Rules (AGENTS.md / influence):**
1. Secrets **never** in git, chat, dash UI, or MCP tool output.
2. **agent-vault** (`oracle`) is the store — references only in code/env.
3. Process env gets secrets **at start** from vault or 0600 files outside the tree.
4. Social **usernames/handles** are public registry data (bgraph / store.json) — not secrets.
5. **Passwords** for platform logins (if stored at all) go in vault as `SOCIAL_<PLATFORM>_PASSWORD` — prefer OAuth tokens over passwords; password login is for claim/validation only.
6. Dash vault UI: values never render — seal only.
7. Rotate on leak; secret-scan before push:
   `grep -rIlE "cfat_|ghp_|sk-[A-Za-z0-9]{10,}|AKIA[0-9A-Z]{16}" --exclude-dir=node_modules --exclude-dir=.venv .`

**Canonical vault key names (OddHobb):**
| Platform | Username (public) | Secret keys (vault) |
|----------|-------------------|---------------------|
| X | `@oddhobbstudio` | `X_API_KEY`, `X_API_SECRET`, `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` |
| Instagram | `@oddhobbstudio` | `META_APP_ID`, `META_APP_SECRET`, `IG_USER_ID`, `IG_ACCESS_TOKEN` |
| TikTok | `@oddhobbstudio` | `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN` |
| YouTube | `@oddhobbstudio` | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` |

**Where usernames live (not vault):**
- `bgraph/registry/brands/oddhobb.json` branches
- `oddhobbies/stores/oddhobb/store.json` → `identity.socials`
- influence passport `influencer.handle` + claim kits

**OTP / validation codes:** always land on brand phone → `phone.agentcom.org` / dash Notifications. Never store OTPs.

---

## 3. Login chain + validation (human-in-the-loop)

```
1. Human creates platform account (browser) with:
     email  hello@oddhobb.com  (or brand Google for YT)
     phone  +44 7822 000802
2. OTP / validation email → cmail + phone agentcom inbox (live on dash)
3. Human creates developer app (per platform) → OAuth once
4. Tokens → agent-vault (human or CLI, never chat)
5. Dash/mark_resource_done on claim-* when handle live
6. bgraph branch ready_to_claim → claimed
7. Publishing tools become live (still human_confirm on send)
```

**Do not** automate platform password login (ToS + CAPTCHA). OAuth app tokens are the correct path for agents.

---

## 4. Target: pi MCP for posting

**Design:**
- Local MCP server `social_publish` (stdio) wrapping stevejobless adapters.
- Tools (all **draft-first**, publish requires human confirm flag):
  - `social.accounts` — list connected platforms + status (no secrets)
  - `social.draft` — create draft post (text, media URL, platform, brand)
  - `social.publish` — publish ONE draft; requires `confirm:true` + optional `task_id`
  - `social.status` — last publish result / post id
  - `social.requirements` — char limits, media rules per platform
- Pi extension pattern (like `funnylabs/pi-extension/content-sensor.ts`): spawn MCP once, register tools.
- Dash chat can call same tools via influence MCP (human digit 7 = confirm).

**Flow:**
```
pi / dash chat → social.draft → queue
human: 7 approve → social.publish confirm:true
adapter → platform API → receipt → Notifications/Agents feed
```

**X cost control in tool:** refuse auto-append of URLs; warn if body contains `http` ($0.20).

---

## 5. Session TODO list (execute in order)

### P0 — credentials + claim completion
- [ ] Confirm OddHobb accounts claimed: X, TikTok, IG, YouTube (report DONE from dash)
- [ ] Human: X developer app → 4 keys → vault `X_*`
- [ ] Human: Google Cloud YT OAuth → `YOUTUBE_*` (+ publish OAuth app to avoid 7-day refresh death)
- [ ] Human: Meta app (Instagram Login path preferred for own account) → vault `META_*` + `IG_*`
- [ ] Human: TikTok developer app + Content Posting → vault `TIKTOK_*`
- [ ] Secret-scan + confirm no keys in git/chat

### P1 — wire our publisher (no Postiz)
- [ ] `pip install tweepy` in stevejobless venv
- [ ] Smoke: adapter `publish` with **unlisted/private** or dry-run against test
- [ ] Dash `social.publish` REST + human_confirm gate
- [ ] Influence MCP tools mirroring pi MCP
- [ ] Receipts on successful publish into `dash/receipts.jsonl`

### P2 — pi MCP extension
- [ ] Create `influence/pi-extension/social-publish/` (or stevejobless) MCP stdio server
- [ ] Register in pi `models`/extensions like content-sensor
- [ ] Tools: accounts, draft, publish(confirm), status, requirements
- [ ] Test: pi drafts X post → human confirm → live post id in chat

### P3 — content + ops
- [ ] Wave 1 heroes: KEYCHAIN-BRICK, XMAS-3D-ORNAMENT, CHARM-* (human_confirmed=1 already for some)
- [ ] Host media on public URL (R2 or oddhobb.com) for IG/TikTok pull
- [ ] Cadence: 1 plain X post/day no-link until paid strategy decided
- [ ] TikTok audit submission once Direct Post works self-only

### P4 — optional hosted MCP (if self-host pain)
Only if P1–P2 stall — **paid SaaS**, not preferred:
- PostZen `mcp.postzen.dev` · Outstand `mcp.outstand.so` ($19/mo) · PostWire · Postfast
- User said no paid Postiz — treat these as fallback only

---

## 6. Success criteria for next session

1. pi (or dash chat) can say: “draft a TikTok caption for XMAS-3D-ORNAMENT” → draft exists
2. Human confirms → adapter publishes → post id + receipt visible in Agents feed
3. No secret ever appears in chat, dash, or git
4. X cost ≈ $0.015/post if no URL in body
5. Phone OTP path still works for any re-auth

---

## 7. Open questions for owner

1. X: pay-per-use credits (~$20 load) OK for now?
2. YouTube: publish OAuth app now (avoids 7-day testing token death) or accept weekly re-auth?
3. Instagram: Instagram Login (no Page) vs Facebook Login (Page) — prefer **Instagram Login** for OddHobb?
4. TikTok: OK with SELF_ONLY until Content Posting audit?
5. First live post platform priority: **X → YouTube → TikTok → IG**?

---

*Sources checked 2026-10-06: X API pay-per-use pricing (docs + secondary), tweepy OAuth1 VPS pattern, Meta IG Content Publishing, TikTok Content Posting get-started, YouTube Data API auth + upload, agent vault / secrets patterns, hosted social MCP options.*
