# PROGRESS — full report, 2026-09-10

## Shipped today (all live, all verified)

**Comms + names**
- cmail worker: inbound pipeline, D1/R2/DO, 14-tool MCP, drafts queue, injection quarantine (live-fired attack quarantined, queue untouched)
- domainnamechecker v3.3.0: +12-surface handle map (socials/packages/ENS, honest unknowns), `claim_kit` MCP, additive UI tab, existing flows byte-identical

**Brain (stevejobless, 92 tests)**
- Tradie pipeline: kernels, intake (voice/WA/IG/SMS/email), quotes, slots (live-Gcal-preferring), confirm, lifecycle, invoices/VAT, CSV, tax quarter
- Job feed with per-consumer ordering (proven live: sparky vs flowright rank differently)
- Scoring + calibration bands, autonomy levels, PII redaction, 90-day transcript sweep
- Backends: Telnyx (numbers/wire/voice+SMS webhooks), LiveKit SIP-config, Google OAuth/freebusy, 3 registrar providers (CF/Porkbun/name.com) with cheapest-under-cap auto-pick
- Domain deals: prepare→approve→register→wire state machine, receipts; name.com dev REGISTERED live, CF path built, blocked only on dashboard contact step (dropped per owner)
- Unified read-only MCP (6 tools), agent profile, SKILL.md onboarding, desk UI, systemd persistence (service+tunnel+backup+sweep timers)

**Docs/repo**: README, AGENTS.md, GUIDE, RECIPES, API, ARCHITECTURE, SECURITY, REPRODUCE, MCP-future, NORTHSTAR, THREADS (A/H triage), BOOTSTRAP, HANDOVER, voiceagentfeedback (review+P0s+contract+build list for voice track). Pushed to `prx0r/cmail` throughout.

## Live URLs

- Desk: `steve.intelligentothers.xyz/desk` · Brain MCP: `…/mcp` · Inbox: `cmail.tradesprior.workers.dev/ui/` · Names: `domainnamechecker.tradesprior.workers.dev`

## Blocked on humans (8, THREADS.md H1–H8)

MX call (last unverified hop) · Meta tokens · Google grant · Telnyx key · Porkbun key · Paid flip · token rotation · pilot business. Zero code blockers.

## Next autonomous (A4–A7)

IG fixtures · secret rotation · pilot dry-run · calibration v2. Voice P0 re-audit waits on the other agent.
