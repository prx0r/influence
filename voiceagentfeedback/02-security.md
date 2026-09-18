# 02 — Security findings (fix before real callers)

Ordered by blast radius. Every item has file:line + concrete fix. None of
this is hypothetical — each is reachable from an unauthenticated request today.

## P0.1 Open API: anyone mints LiveKit publish tokens

`POST /cases/{id}/join` (`app/main.py:128-136` → `app/session.py:23-45`) mints
a LiveKit JWT for an arbitrary `identity` with zero caller verification, and
`case_id` is `case_` + 8 hex (`app/cases.py:17`) — enumerable. An attacker gets
a publish-capable token into your agent's room: eavesdrop, inject audio, burn
your LiveKit bill.
**Fix**: API key on all routes; unguessable case IDs (`secrets.token_urlsafe`);
token mint restricted server-side (never mint for network-supplied identity).

## P0.2 Safety is prompt-and-hope

`escalation.safety` nodes exist in YAML, but `main.py` never checks retrieval
hits for `type==escalation`, `flow.classify_intent` has no URGENT/SAFETY class,
guard has no safety tripwire. If the LLM doesn't comply on a gas-leak call,
* recreationally nothing happens* — no event, no ticket, no callback.
**Fix**: deterministic classifier (`app/urgency.py`): safety-keyword +
escalation-node hit → auto `escalation.requested` + priority ticket + stop
diagnosing + urgent intake to us (`urgent:true` → our priority-100 action).
Never let the model be the only thing standing between a caller and harm.

## P0.3 PII stored raw everywhere

`store.add_message(sid,"user",inp.message)` (`main.py:45`) persists passwords,
phones, addresses verbatim into SQLite, case JSON, and audit logs. Your own
test proves the model gets *asked* for passwords; nothing redacts.
**Fix**: scrub phone/email/address/password patterns before every write
(`main.py:45,74`, `store.py:14-16`, `cases.py:80-81`, audit writers), plus a
TTL/purge for recordings/transcripts. Our side already TTL-sweeps transcripts
at 90 days and redacts exports — mirror it.

## P0.4 Confirm flow is brute-forceable + amnesiac

`secrets.token_hex(4)` = 32 bits (`ittools.py:52`), no rate limit on
`execute_fix`. `OUTSTANDING`/`SEEN_KEYS` are in-process dicts: restart bricks
pending fixes, unbounded growth, cross-session replay quirks.
**Fix**: 128-bit tokens, rate-limit execute, persist outstanding to SQLite,
namespace idempotency per session. And soon: retire the local confirm flow for
business actions entirely and use our approval tokens (single-use, sha256,
drift-guarded) — one confirm system, ours, audited.

## P0.5 Real subprocess behind LLM-controlled args, no allowlist

`restart_process` runs `pkill -f <name[:64]>` (`ittools.py:76`) — attacker text
kills arbitrary processes. `ping_gateway` takes any host (SSRF-ish).
`read_logs unit` → `journalctl -u <unit>` exfiltrates beyond the business.
`REFUSE` is a substring blocklist on dumped args — bypassable (`pass_word`,
actions never scanned).
**Fix**: allowlist restart targets, constrain hosts/units, scan action names
too. Long term these IT tools don't belong in the customer-facing agent at
all — split silver (customer) / red (operator) toolsets.

## P1 hardening (next pass)

- **Input guard**: you enforce output (`guard.py` twice per turn — good) but
  never classify input. Add tool-arg validation + citation verification (you
  ask the LLM for citations at `llm.py:28` but check nothing).
- **`JSON_RE = \{.*\}` is greedy** (`llm.py:5`); non-JSON falls back to raw
  model text as the answer (`llm.py:47-48`), bypassing tool-path expectations.
- **Secrets hygiene**: `.env`-only creds, no vault. We run `agent-vault`
  (proxy-attached credentials the agent never sees) — adopt the pattern or at
  minimum add `.env.example` + rotation notes.
- **Guard coverage**: 4 tripwire classes, all about persona/policy. Add
  price/availability fabrication (unhedged numbers) and fake-identity-document
  classes — these are your revenue-adjacent lies.
