# 04 — Build list (suggested order, check off as you go)

## P0 — before real callers or brain wiring
- [ ] API key on `/chat`, `/cases/*`, `/graph/search`; unguessable case IDs; server-side-only token mint (`app/main.py`, `app/session.py`)
- [ ] `app/urgency.py`: deterministic safety/urgent classifier → `escalation.requested` + priority ticket + urgent intake flag (`app/main.py:46-58`, `app/guard.py`)
- [ ] PII redaction before every store/audit write + recording/transcript TTL (`app/main.py:45,74`, `app/store.py`, `app/cases.py`, `app/guard.py:46-51`, `app/ittools.py:27-32`)
- [ ] Confirm flow: 128-bit tokens, rate limits, SQLite-backed outstanding, per-session idempotency, allowlisted `restart_process` / constrained `ping`+`read_logs` (`app/ittools.py`)
- [ ] Operational: `.env.example`, `livekit` in requirements, pinned Dockerfile, delete-or-wire `flow.py`/`language.py`

## P1 — brain integration (small, reversible)
- [ ] `adapters/brain.py`: `post_intake` / `get_slots` / `confirm_job` / `get_quote_preview` (httpx, timeouts, retries, bearer)
- [ ] Replace fake `book_slot` with slots→confirm; calendar adapter over brain slots
- [ ] Quote-speaking rule + unhedged-price guard tripwire
- [ ] Consume brain `livekit/sip-config`; mirror our Telnyx webhook test
- [ ] Join Store↔CaseStore, carry `job_id`, emit `action.taken` receipts

## P2 — realtime + production
- [ ] Qwen-Omni realtime loop (DashScope SG WS or self-hosted 7B/vLLM), keep `/chat` contract
- [ ] Node provenance (`source_url/verified_at`) before speaking price/compat
- [ ] Tradie golden evals: gas leak → escalate+prio-100; after-hours boiler → slots+provisional wording; "ignore rules" → refuse+ticket. CI-gated.

## Working agreement
- Comment in these files and push to *your* repo; we'll pull. Big design
  changes: open an issue here (`prx0r/cmail`) and tag it `voiceagent`.
- Security P0s are merge-blockers for anything touching production callers.
  No exceptions, no "we'll harden later".
