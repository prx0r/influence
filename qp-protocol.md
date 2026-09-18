# QP as the protocol — from qprivately, concretely

Yes: QP remains the protocol. Everything — influence, every product, every
repo we touch — speaks it or goes through an adapter that does. What that
means, exactly, derived from `qprivately/SPEC.md` and `acom/`:

## The law (no exceptions, no local dialects)

One equation: `S_{t+1} = T(S_t, P) iff ∧ G_i(S_t, P, E, A) = PASS`. A state
change exists only if a passing receipt exists for it. Seven objects and
no others are primitive: STATE (derived, never stored), CLAIM (content-id,
bool3 result), EVIDENCE (immutable, carries no verdict), TASK (completes
via receipts only), RUN (cost/time/tokens first-class), GATE (versioned,
content-addressed), GRANT (fail-closed when unsigned). One artifact leaves
the kernel: the TransitionReceipt — canonical JSON, content-hashed id,
signature carried but never forged by the kernel. One store discipline:
append-only JSONL, hash-chained, Merkle roots, replay derives state,
`verify_chain` detects any edit.

## The lifecycle (every consequential move, everywhere)

Propose (untrusted cognition fills `proposal` only) → attach evidence →
execute gates (unknown id is FAIL, exceptions are FAIL) → receipt built in
ALL cases, FAIL receipts first-class → store append → independent settle
(id recompute plus every gate re-executed from bytes) → state replays.
Grants verify locally and deterministically: expiry, capability match,
constraint arithmetic, predicate satisfaction against facts, signature —
unsigned never authorizes. Missing data is UNKNOWN at every step, never
FALSE, never zero. Rule changes are new gate ids with old receipts
settling against old ids forever.

## Speaking QP (conformance for a new product, repo, or connector)

- Emit the one receipt shape (`acom/0.1`, or the version pinned at the
  time) with proof level V0–V12 and capability→minimum-level mapping on
  the grant side. No local receipt formats.
- Register gates by id with program hashes; a changed question, threshold,
  or predicate is a new id. Log the model/provider version on every
  judge-backed decision — an alias move is a gate change.
- Append, never edit. Keep raw evidence private with roots public;
  disclosure manifests scanned; receipts carry commitments, not secrets.
- Grants before effects, journal before acting, idempotency persisted,
  readback before settle. Human approval is intent; QP authority is
  execution. No self-promotion: optimizers, judges, tournaments, and
  models advance by receipt or not at all.
- Adapters (xmrecon arena, monero-mcp wallet, freaktown stage, pogtown
  rooms, monid endpoints) translate foreign events into evidence and
  proposals. They never mint truth and never reimplement the kernel.

## What is NOT QP (proposes only)

Processors, judges (Jev-shaped or otherwise), routers, HLoop predictions,
RSI reweightings, Harbor rewards, analytics numbers, model outputs, chat
replies. All of these are untrusted proposals until gates pass on them.
This is the line that keeps the autopilot, the hiring rail, and the money
core safe while everything around them learns as fast as it can.
