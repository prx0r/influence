# THREADS — what machines do vs what humans do, in priority order

## 🤖 Autonomous (no human needed — work top to bottom)

| Pri | Thread | Why first | Definition of done |
|---|---|---|---|
| A1 | **Scheduled reconcile sweep** | DONE live (06:00 timer, verified 200s) |
| A2 | **Push-flow script** (was T17) | kills the copy-divergence risk (T16) before it bites | one command: re-sync `/tmp/cmail-repo` ← `/root`, secret-scan, commit, push |
| A3 | **Unified MCP, read-only** | DONE live (`POST /mcp`, 6 tools, verified) |
| A4 | **IG lead test harness** (part of T10) | proves the bridge without Meta tokens | fixture payloads → jobs, continuity asserted in suite |
| A5 | **Secret rotation runbook + TEST_INGEST_SECRET rotate** (T18, T8-support) | hygiene with teeth | new secret in worker + steve env, old revoked, verified live |
| A6 | **Second pilot dry-run** (supports T11) | de-risks the real onboarding | full SKILL.md pass against fixture business, gaps logged |
| A7 | **Calibration weights v2** (supports T12) | ready the day real jobs close | documented weight proposal from synthetic distribution, flagged provisional |

## 🧑 Human (keys, clicks, calls — each 2–15 min)

| Pri | Thread | Action | Unblocks |
|---|---|---|---|
| H1 | **Inbound MX call** (T1) | confirm tantrafiles root mail disposable, or name a fresh domain | last unverified hop in the whole system |
| H2 | **Meta tokens** (T4) | WhatsApp Cloud API + IG page token + verify tokens | real customer messaging (biggest pilot unlock) |
| H3 | **Google OAuth grant** (T7) | open auth-url, paste code | live freebusy + event creation |
| H4 | **Telnyx key** (T6) | account + API key | real numbers, voice wiring, SMS delivery |
| H5 | **Porkbun key** (T5) | account + key (sandbox free) | excluded-TLD buys, cheapest-provider competition |
| H6 | **Workers Paid flip** (T3) | $5/mo on migration day | outbound email |
| H7 | **GitHub token rotation** (T8) | new token, replace in chat/vault | closes the chat-history exposure |
| H8 | **Second pilot business** (T11) | who + 15-min session | real data for calibration, VAT, photo-ask tuning |

## 📋 Standing / background (no action unless signal changes)

- **Copy-repo divergence** (T16) — mitigated by A2, then delete this line.
- **Live DB single SQLite** (T19) — backups cover it; revisit at real revenue.
- **Upstream git leftovers** (T20) — this repo is source of truth; ignore.
- **Tax handoff** (T14) — waits on first real invoice (→H8).
- **Voice P0 re-audit** (T15) — waits on other agent; verify before production callers.

## Closed (do not reopen)

Repo docs · push script (`scripts/sync-push.sh`) + `BOOTSTRAP.md` (repo runs itself now) ·

R2 backups · drafts UI · renewal sync · quarantine · call-back gate · VAT ·
feed ordering · 3 registrar providers · handles + claim_kit · registrar token ·
repo docs · this triage.
