# CRED-BROKER — social credentials + agent posting + OTP

> Agent never holds raw secrets. Vault holds tokens. Publisher holds sessions.
> OTP codes flow inbox → human confirm → submit. Nothing auto-posts.

## Rules (non-negotiable)

1. **Secrets in vault only** (`agent-vault`, vault `oracle`). Never in tree, never in chat-pasted files, never in R2. 0600 files only. Secret-scan before every push.
2. **OAuth tokens, not passwords.** No screen-scraped logins (ToS breach, fragile). Each platform = dev app + OAuth + refresh.
3. **Agent calls publisher, never the platform.** Agent passes `{slug, platform, draft_id}` + approval token. Publisher injects the token server-side.
4. **Publish + OTP submit both need human_confirm** (dash digit 7 / approval token). Agent drafts, human flips.
5. **Two brands, two credential sets.** oddhobb and pogtown never share tokens. `store_id` on every vault name.

## Vault names (only names live here)

| Platform | Vault names (`oracle`) | Notes |
|----------|------------------------|-------|
| X (oddhobb) | `X_API_KEY_ODDHOBB`, `X_API_SECRET_ODDHOBB`, `X_ACCESS_TOKEN_ODDHOBB`, `X_ACCESS_TOKEN_SECRET_ODDHOBB` | account `@oddhobb` |
| X (pogtown) | `X_API_KEY_POGTOWN`, … same suffix | account `@pogtown` (unclaimed) |
| IG (oddhobb) | `META_APP_ID_ODDHOBB`, `META_APP_SECRET_ODDHOBB`, `IG_USER_ID_ODDHOBB`, `IG_ACCESS_TOKEN_ODDHOBB` | `@oddhobbstudio` |
| TikTok (oddhobb) | `TIKTOK_CLIENT_KEY_ODDHOBB`, `TIKTOK_CLIENT_SECRET_ODDHOBB`, `TIKTOK_ACCESS_TOKEN_ODDHOBB` | `@oddhobb` |
| YouTube (oddhobb) | `YOUTUBE_CLIENT_ID_ODDHOBB`, `YOUTUBE_CLIENT_SECRET_ODDHOBB`, `YOUTUBE_REFRESH_TOKEN_ODDHOBB` | `@oddhobbstudio` |
| Pinterest | via Shopify sales channel (no separate secret) | see store.json |
| cmail auth | `CMAIL_*` (existing) | inbox read |
| phone | `ODDHOBB_PHONE_AUTH`, `TELNYX_*` (existing) | SMS read |
| Site logins (owner-set 2026-10-08) | `X_PASSWORD_ODDHOBB`, `INSTAGRAM_PASSWORD_ODDHOBB`, `ETSY_PASSWORD_ODDHOBB`, `TIKTOK_PASSWORD_ODDHOBB` | static, vault `oracle`. Usernames = confirmed handles (X `@oddhobb`, IG `@oddhobbstudio`, Etsy `oddhobbstudio`, TikTok `@oddhobb`). Prefer OAuth tokens long-term; passwords are fallback for login flows. |

bgraph `branches[].account.auth_ref` points at these **names**, never values.

## Publisher (separate service, API only)

```
POST /publish/draft   {slug, platform, text, media_r2} -> {draft_id}
POST /publish/approve  {draft_id, approval_token}      -> {scheduled|queued}
POST /publish/status   {draft_id}                      -> {state, platform_id, analytics}
GET  /analytics/pull   ?slug&platform                  -> R2 content/stores/<id>/analytics/<platform>/
```

- Tokens live in publisher env (vault-injected at boot), refreshed per platform rules.
- Human previews the draft in dash/Postiz calendar, hits 7, publisher posts.
- Every post writes a QP receipt (draft_id, platform_id, ts).

## OTP flow (verification codes)

Platforms send codes to brand email or the shared phone:

- Email: `hello@oddhobb.com` / `hello@pogtown.com` → cmail worker → `email.inbox {mailbox}` → `email.read {message_id}` → extract 4-8 digit code.
- SMS: `+447822000802` → Telnyx → `phone.agentcom.org` → `phone.sms {slug}` → extract code.

Flow:
```
1. Agent triggers login/OAuth on publisher (draft-side only, no secret)
2. Platform sends code -> inbox
3. Agent reads inbox (MCP), shows code + context to human, does NOT submit
4. Human confirms (digit 7 / approval token)
5. Publisher submits code, stores session/refresh token in vault, reports back
```

Codes are short-lived (5-10 min). Agent polls inbox max 3x, then asks human to paste manually. Manual paste path: human drops code in dash chat → agent forwards to publisher with the same approval token.

## Publisher: x-manager (`/root/xman`, MIT)

Self-hosted X scheduler, live on `:3999` (Node 22 at `/opt/node22`, SQLite `var/`).
3 account slots, in-app scheduler 60s, approvals, Bridge API for bots, agent manifest at `/api/system/agent`.

| Slot | Brand | X handle | Vault token names (oracle) |
|------|-------|----------|----------------------------|
| 1 | oddhobb | `@oddhobb` | `X_API_KEY_ODDHOBB` + user tokens on connect |
| 2 | pogtown | `@pogtown` | `X_API_KEY_POGTOWN` + user tokens on connect |

- One X dev app (Read+Write) for both; per-account OAuth via xman First-Run Setup UI. Admin token + encryption key live in `/root/xman/.env` only (gitignored, never commit).
- Agent path: pi/dash drafts → xman `/api/scheduler/posts` (or Bridge API) → human approve in xman UI → scheduler posts → analytics back to R2.

## What to give me (when ready, one platform at a time)

X first (confirmed `@oddhobb`): dev-app key/secret + access token/secret — paste into vault directly (`agent-vault vault credential set … --vault oracle`), never into chat. I verify with a read-only call (`GET /2/users/me`), then draft-only mode until you approve the first publish.
