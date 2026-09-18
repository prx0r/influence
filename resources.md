# Resources — registry of everything we learn from

Each entry: what it is, where it lives, pin/status, and how it applies to
us. Sources are references, never runtimes — we port patterns, not code,
and pin versions before relying on behavior.

## awesome-rsi (`lobehub/awesome-rsi`)

Research map of Recursive Self-Improvement: fundamentals, model-level
(self-reward, self-play, STaR), harness-level (prompt optimization,
memory evolution, scaffold evolution, self-evolving frameworks),
multi-agent co-evolution, coding self-improvement, automated AI R&D,
evolutionary/open-ended methods, safety (goal drift, misevolution,
sandbagging, reward tampering), benchmarks.

- Applies: vocabulary and loop designs for our RSI (post-hoc optimizer)
  and HLoop. Directly liftable: memory-evolution patterns (ExpeL-style
  insight extraction from run histories), harness-evolution discipline
  (bounded edits, held-out validation gains — matches our promotion rule),
  self-verification foundations for judges, and the safety shelf
  (misevolution, goal drift, reward tampering) as required reading before
  the autopilot loop opens. Benchmarks section is where our frozen eval
  design gets compared before we invent our own.

## Jev knowledge gist (`pjburnhill` gist `adf8d28e`)

Project reference for TypeSafe Jev: primitives (Noul/Choice/Score),
state design, probability + confidence semantics, calibration vs
correctness, parallel evaluation, suitability test, preferred
code-judges-code architecture, task shapes (classify/detect/score/route/
search/rank).

- Applies: question-design rules for every judge in `product-schemas.md`
  (one narrow question, concrete level definitions, `other` outcomes,
  fan-out then compose in code). The cautions are load-bearing for us:
  calibration ≠ correctness (hence per-family thresholds + human rail),
  schema-safe ≠ error-free (hence frozen evals), serial calls only for
  genuine information dependencies (hence our present→decide ordering).
  The suitability test (5–6 yeses) gates whether a new judge is Jev-shaped
  or needs a reasoning model.

## monid (`monid-ai/monid`, MIT — cloned to `/home/ubuntu/monid-upstream`)

OpenRouter for agent tools: declarative provider + endpoint definitions,
per-call endpoint choice via `discover` (price, health, latency),
usage metered per call settled on the raw response envelope before output
mapping (vendor errors settle at zero), sealed content-hashed execution
units, credentials injected inside the transport never the engine,
replay-from-fixture tests with no network, resources with lifecycle
(provision/verify/release/reconcile) for owned things like phone numbers.

Studied in-tree (this is the highest-value clone of the three):

- `connectors/saperly/resources/phone-number/resource.ts` is our number
  bridge already designed: verify-before-charge (404 ⇒ inactive, other
  non-2xx THROWS and retries — never conclude from a flaky read),
  idempotent release with stable keys, refresh semantics where the
  E.164 carries forward on degraded reads but the upstream pointer is
  AUTHORITATIVE (absence clears it), observed usage returned for the
  drift channel. Lift the whole shape for number.provision.
- `provision-numbers/endpoint.ts` runs the 4-call saga quote →
  connection-first → buy (one PriceChanged retry under a distinct key) →
  bind, with `{runId}:<op>` idempotency on all writes. That saga is our
  prepare-approve-register-wire pattern, already debugged.
- `connectors/exa/provider.ts` shows vendor-claimed cost receipts
  cross-checked against pinned rates — our attempt-vs-readback split in
  executable form. Adopt for registrar/renewal drift detection.
- `connectors/kling/` (text/image-to-video across 2.5–3.0) are ready-made
  clip-farm render providers behind the same contract.
- `engine/transport.ts` + `shared/testing/` give the hermetic discipline:
  trimmed recorded fixtures with size lint, replay Fetch, redacted query
  values, live tests gated on env creds and skipped otherwise. Adopt per
  connector alongside the pq live-fire tests.
- Applies: our L1/L2/L4 providers take monid endpoint shape; `discover`
  ranking is our capability-matrix selection; sealed units are our
  no-second-kernel rule executable; credentials-in-transport is our vault
  story converged. Credentials convention (`<NAME>_CREDENTIALS_<FIELD>`,
  no silent fall-through) is worth copying verbatim.

## Previously stored

- Kill Tony corpus: `jacob-burgess/killtony` @ `8f64531`,
  `/home/ubuntu/killtony-upstream`. Comedy style reference + frozen eval.
- awesome-jev (`Anil-matcha/awesome-jev-by-typesafe`): 31 use cases,
  production loop, safety checklist. Judge-side patterns.
- Refix Jev TypeScript quickstart: `systemOne` call shape, confidence
  gating, model pinning. First-integration template.
- TEE references: `pdash/docs/private_compute/` (NanoGPT, Phala).
  Attestation flows for the private-studio connectors.
