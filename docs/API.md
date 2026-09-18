# API — endpoint reference

Brain base `/api`. Bus base `/`. Checker base `/`.

## Tradie (`/api/tradie/{slug}`)

| Method + path | Purpose |
|---|---|
| `GET /kernel` · `PUT /kernel` | read/replace kernel (price book, prefs, autonomy) |
| `POST /intake` | voice/chat intake → job + action + options (autonomy-gated) |
| `GET /jobs?status=` · `GET /jobs/{id}` | list / detail + transcript + quotes + options |
| `PATCH /jobs/{id}` | status/schedule/price/duration/note |
| `POST /jobs/{id}/quote` | draft from price book (never sends) |
| `POST /jobs/{id}/quote/{qid}/send` | confirm → WhatsApp; ≥threshold needs `/callback` first |
| `POST /jobs/{id}/callback` | record voice verification |
| `POST /jobs/{id}/quote/{qid}/email_draft` | queue draft in cmail |
| `POST /jobs/{id}/sms` | SMS confirm (live with Telnyx, stubbed without) |
| `POST /jobs/{id}/invoice` · `GET /invoices` · `GET /invoices.csv` | invoice + accountant export |
| `GET /tax/quarter?year=&q=` | net/vat_owed/gross |
| `GET /slots` · `POST /jobs/{id}/confirm` | availability → booking |
| `GET /jobs/{id}/calendar.ics` | one-click calendar file |
| `GET /stats` | per-type stats + calibration bands |
| `POST /score` | score any candidate job |
| `POST /sweep?confirm=true` | purge transcripts past retention |
| `POST /reconcile` | channel/backend states (7+ keys) |
| `GET /social/claim-kit?name=` · `POST /social/verify` | handle map + claim verification |
| `GET /whatsapp/webhook` · `POST /whatsapp/webhook` | Meta verify + inbound |
| `GET /instagram/webhook` · `POST /instagram/webhook` | same for IG |
| `GET /feed?for_slug=` | cross-business scored feed |

## Backend (`/api/backend`)

| Method + path | Purpose |
|---|---|
| `POST /{slug}/telnyx/credential` · `GET /{slug}/telnyx/numbers` · `POST /{slug}/telnyx/wire` | number setup + webhook wiring |
| `POST /telnyx/voice-webhook?slug=` · `POST /telnyx/sms-webhook?slug=` | call/SMS events → jobs |
| `GET /{slug}/livekit/sip-config` | trunk JSON for voice side (409 until numbered) |
| `POST /{slug}/gcal/auth-url` · `POST /{slug}/gcal/callback` · `POST /{slug}/gcal/calendar` · `GET /{slug}/gcal/status` | Google OAuth + calendar pick |

## Domains (`/api/domains`)

`GET /providers` · `GET /check?domain=&provider=` · `POST /claim` ·
`POST /prepare` · `POST /{id}/approve` · `POST /{id}/register` ·
`POST /{id}/wire?worker=` · `GET /deals` · `GET /{id}` (receipt) ·
`GET /renewals` · `POST /renewals/sync` · `POST /creds`

## Observations (`/api/observations/email`)

Single POST: classification-aware intake (quarantine → prio-15 review, receipt
→ nothing, job-like → job + action). Dedupes on `email:{message_id}`.

## cmail worker

`/api/inbox` · `/api/stats` · `/api/drafts` (GET list, POST queue, secret) ·
`/admin/address` · `/admin/alias` (ADMIN) · `/test/ingest` (secret) ·
`/mcp` (14 tools; `email.send` needs `confirmed:true` + Paid+SENDER) · `/ui/`

## Checker worker

`/api/verify/:domain` · `/api/registrar/:domain` · `/api/mine` ·
`/api/bulk-verify` · `/api/search` (SSE) · `/api/handles/:name` ·
`/mcp` (8 tools incl. `check_handles`, `claim_kit`) · `/api/health`
