# Voice-agent compat contract (steve/cmall ⟷ Qwen-Omni voice side)

Ownership split — voice owns conversation, brain owns business:

```
voice agent (Qwen-Omni realtime)          stevejobless + cmail (this side)
─────────────────────────────           ──────────────────────────────────
live call / chat, intent, photos          tradie kernel (price book, prefs)
transcript, urgency judgement             jobs, quotes (drafts), scheduling
wake-now voice reply                      HumanAction queue, stats, scoring
                                          WhatsApp/IG/FB/email send-out
```

## Shared: the kernel YAML

`stevejobless/knowledge/<biz>_en.yaml` IS a valid voice-agent BUSINESS_CONFIG.
`business/agent/voice/nodes` drive the voice graph; the extra `tradie:` block
(price book, preferences, multipliers) is read here and ignored there.
One file, two consumers, zero drift.

## Voice → brain: call intake

`POST /api/tradie/{slug}/intake`
```json
{"customer_name":"…","customer_phone":"…","customer_address":"…",
 "channel":"voice","job_type":"ev_charger","description":"…",
 "transcript":"…","urgent":false,"after_hours":true,"distance_km":12}
```
Creates Job + transcript + HumanAction (urgent → priority 100 wake-now).
Returns one-click options: quote draft, ICS calendar, call-back, verdict.

## Telephony handoff (Telnyx + LiveKit — brain side owns setup)

- Numbers + webhooks: `POST /api/backend/{slug}/telnyx/credential`, then
  `/telnyx/wire` with `{connection_id, phone_number, base_url}`. Completed
  calls auto-open jobs at `/api/backend/telnyx/voice-webhook?slug={slug}`.
- SIP wiring the voice agent applies: `GET /api/backend/{slug}/livekit/sip-config`
  (trunk + dispatch rule + egress webhook; fix listed `problems` first).
- Slots the agent may speak: `GET /api/tradie/{slug}/slots` (live Google
  freebusy when connected, scheduled-job blocks otherwise). Confirm with
  `POST /api/tradie/{slug}/jobs/{id}/confirm {"scheduled_at":…}`.

## Brain → voice: quote drafts worth speaking

`GET /api/tradie/{slug}/jobs/{id}` → `options[].preview` is the exact
customer-facing wording; voice agent may read it verbatim once
`needs_review=false`, otherwise it must say "provisional".

## Channels

- WhatsApp native via Meta Cloud API (`channels.py`). Needs vault creds
  `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`
  — absent → stubbed sends, full workflow testable.
- SMS confirm: stubbed (`send_sms`) — wire Twilio/Telnyx on request.
- Email in/out: cmail `/mcp` (live). IG/FB posting: Postiz + publisher
  adapters (live in stevejobless).

## Metrics that matter

- qualify→survey conversion (photo-ask weight is tunable in kernel; <40% → trim to 2 photos)
- verdict accuracy: score vs actual margin/hassle on done jobs (stats endpoint)
- response latency: intake → first customer-facing draft

## Muse verdict (researched 2026-09-10)

Muse Code + Muse Spark (dev.meta.ai, OpenAI-compatible API, 1M ctx) is a
*coding* agent and model API — the thing you build WITH, not the thing
tradies talk to. It has no voice/telephony/WhatsApp runtime. Recommendation:
build the voice runtime on Qwen-Omni realtime (DashScope Singapore WebSocket,
or self-hosted Qwen2.5-Omni-7B under vLLM), keep the business brain here,
and optionally use Muse Code as a dev accelerator. Do not route tradie
traffic through it.
