# 03 — Integration contract (both sides)

Rule: **you own conversation, we own business.** Don't reimplement anything in
the right column; we won't touch the left.

## Calls your side makes (all live, verified today)

| # | Purpose | Endpoint | Notes |
|---|---|---|---|
| 1 | Call/chat intake (**every** conversation ends here) | `POST /api/tradie/{slug}/intake` | Body: name/phone/address/channel/job_type/description/transcript/`urgent`/`after_hours`/`distance_km`. Urgent → priority-100 wake-now action. Returns one-click options. |
| 2 | Speakable slots | `GET /api/tradie/{slug}/slots` | Live Google freebusy when connected, else scheduled-job blocks. Never cache: re-fetch per call. |
| 3 | Confirm booking | `POST /api/tradie/{slug}/jobs/{id}/confirm {"scheduled_at"}` | Two-step with (2), mirroring your propose/execute pattern. |
| 4 | Quote wording | `GET /api/tradie/{slug}/jobs/{id}` → `options[].preview` + `needs_review` | Verbatim **iff** `needs_review=false`, else prefix "provisional". Add a guard tripwire for unhedged price claims. |
| 5 | Telephony setup (we own it) | `GET /api/backend/{slug}/livekit/sip-config` | Trunk + dispatch + egress webhook. Fix listed `problems` first. Send your authenticated caller number through as trusted identity; never let the LLM overwrite it. |
| 6 | Shared kernel | `stevejobless/knowledge/<biz>_en.yaml` | You read `business/agent/voice/nodes`, ignore `tradie:`. Same file also loads as your `BUSINESS_CONFIG` — copy, don't fork. |

## Mismatches to resolve (in order)

1. You have no `urgent`/`after_hours` detector — build P0.2 first or field 1's flags are fiction.
2. Your `book_slot` returns fake `pending_confirmation` — replace with slots→confirm (row 2+3); delete the stub, don't leave both.
3. Carry **both** IDs: your `case_xxxx` + our `job_id` (we dedupe on `resource_key=job:{id}`, same pattern as our email bridge).
4. `tools/calendar.py` + `tools/shopify.py` are `NotImplementedError` — implement calendar as a thin client over rows 2+3, not a parallel calendar. Shopify stays yours if the store lane is real, else delete.

## What we expose for you (already live)

- Intake/quotes/slots/invoices/approvals, WhatsApp/SMS/Telnyx/Google backends,
  `HumanAction` queue, reconcile states, `/.well-known/agent-profile.json`.
- Full spec: `stevejobless/docs/VOICE_COMPAT.md` + `stevejobless/SKILL.md` in this repo.
- Reverse direction later: once your `/cases` has auth, we'll open cases from
  our queue and read `brief()` for the tradie. Not before P0.1.
