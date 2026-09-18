# 01 — What you have (review of `08f19c2`)

## Pipeline today

**Chat** (`app/main.py:42-83`): `POST /chat` → store user msg → graph context →
history → LLM (OpenAI-compatible JSON) → output guard → optional tool call →
second-pass grounded summary → guard again → store → optional Edge-TTS.
No WebSocket/realtime loop, no STT/VAD/barge-in, no Qwen-Omni client yet —
"voice" today is HTTP chat + MP3 playback. That's fine for the stage you're at.

**Calls** (`app/main.py:104-157`, `app/session.py`, `app/cases.py`): case
lifecycle with LiveKit room ensure + token mint + event fold + `brief()` warm
transfer. SIP/Telnyx correctly deferred to the LiveKit layer (`session.py:5-6`).

**Tools**: ticket/callback/slot stubs over SQLite; hours lookup real; order
status stubbed; IT tools real-but-dangerous (see 02-security). Calendar and
Shopify adapters are `NotImplementedError` — good, don't build them; consume
ours (see 03-integration).

## Genuine strengths — keep these

1. **Graph-is-authoritative is enforced, not aspirational**: prompt rule +
   second-pass grounding + evals. This matches our `needs_review` provisional
   quote rule exactly. Same religion, both sides.
2. **Tool-abuse thinking early**: propose→execute split, single-use confirm
   tokens, idempotency receipts, REFUSE→ticket, dual audit trails. Mature
   instincts for a 2-day prototype.
3. **Transport/channel separation**: kernel independent of LiveKit/SIP/TTS
   vendor. This is the correct boundary for our contract.
4. **Case-as-event-log** with `brief()`: the right warm-transfer primitive for
   our `HumanAction` queue. Keep it; we'll carry `job_id` on it.
5. **Pack compiler + schema**: natural dock for the shared kernel YAML.
6. **Evals run without an LLM**; READMEs honest about limits.

## Structural issues (non-security)

- **Two state systems don't talk**: `/chat` → SQLite sessions; `/cases` →
  JSON files. No session↔case join. Fix when wiring intake (03-integration §8).
- **Dead code executing nothing**: `app/flow.py` intent classifier and
  `app/language.py` voice-map are never imported by `main.py`. Either wire them
  or delete — dead safety-adjacent code is worse than none (looks covered).
- **Missing operational files**: no `.env.example` (your own README + run.sh
  reference it — fresh clone breaks), `livekit` missing from requirements
  (configured-room path crashes), Dockerfile unpinned.
- **Graph retrieval won't scale past ~50 nodes** (your own BUILD_NOTES flags
  it). Fine now; provenance fields first, Neo4j later.
