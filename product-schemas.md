# Product schemas — categories, dependencies, and the QP thread

Companion to `products.md` (the what). This is the shape: every product as
the same schema, grouped into layers, with dependencies explicit so we can
see what unlocks what and where QP runs through all of it.

## The one schema (every product fits it)

- Intent: the job in one line.
- In → out: what goes in, what comes out.
- Passport: the resource chain on the graph.
- Connectors: have vs need.
- Judges: the typed decisions, written Jev-style (Choice / Score / Noul).
  Any judge can run on current models via structured output today or on a
  Jev-shaped provider later. Same contract either way.
- Lens: the one dash view.
- QP: which receipts, which gates, what the grant boundary is.

## Layer 0 — substrate (everything stands on this)

P0 graph + queue + receipts (live), P1 private studio (hardening).

- Judges: `privacy_class` Choice (ANON_CORE / PSEUDONYMOUS_BRIDGE /
  IDENTITY_BRIDGED), `needs_human` Noul, `risk` Score.
- QP: transition equation, 7 objects, append-only store, 15 invariants.
  Grants precede spend, QP settles, Harbor eval-only.
- Unlocks: all layers below. Nothing ships without it.

## Layer 1 — spawn (make them exist)

P2 Instant Influencer. P5 birth canal reuses it.

- In → out: concept or trend pointer → handle, domain, zone, mailbox,
  number, claimed socials, first-week drafts.
- Passport: candidates → handles → domain verify → registrar compare →
  prepare-approve-register-wire → zone → mailbox → number → social verify
  → content.
- Connectors have: project, static checklist, domain observe, social
  observe. Need: registrar compare, zone apply, mailbox, number bridges
  (capability-matrix), publisher draft.
- Judges: `handle_set` Choice (pick first-free set + `other` fallback),
  `name_risk` Score, `claim_ok` Noul per social, `spend_ok` Noul with
  drift and budget facts in state (arithmetic stays in code).
- Lens: names + handles, money + grants, verification with receipts.
- QP: per-resource evidence, per-project receipt, FAIL receipts first-class
  until complete. Human confirms spend and sends at every autonomy level.

## Layer 2 — operate (keep them alive, send things out)

P3 Influencer Ops.

- In → out: live influencer → posted content, answered inbox, renewed
  domains, balanced books.
- Passport: content queue → render → gated publish → readback; inbox →
  triage → draft → gated send; renewals → desk actions.
- Connectors need: publisher/postiz, inbox needs-reply, video render
  (desired = spec, observed = artifact hash), YouTube publish (gated),
  YouTube Analytics read-back (read-only).
- Judges: `intent` Choice + `urgency` Score + `needs_human` Noul on every
  inbox item (the ticket-router pattern, straight from the Jev
  quickstart); `delivery_ok` Noul on readback; `drift_ok` Noul on renewals.
  Low confidence → human rail, always.
- Lens: ops board — calendar, inbox, spend. Same task IDs.
- QP: delivery claims settle on readback only, never on attempt. Publishing
  is a grant-backed effect with idempotency keys.

## Layer 3 — create (what they make)

P4 Influencer Studio, freaktown bridge.

- In → out: queued content job → stage artifact (avatar, voice, take) →
  published piece with receipt.
- Boundary: bundles and events cross, never internals. Influence consumes
  freak bundles by digest; freaktown never reimplements the queue.
- Connectors need: sealed bundle import (digest-pinned), stage job
  submit, artifact readback.
- Judges: `bundle_valid` Noul (digest + schema in code, semantic fit as
  question), `quality` Score vs frozen bar, `lineage` Choice (which
  category this belongs to).
- Lens: studio tab — job, evidence root, receipt, approve-deny.
- QP: freak pack digest in the evidence, stage output as artifact hash,
  promotion of a look/voice is a receipt.

## Layer 4 — evolve (get funnier over time)

P5 Autopilot + P6 watch loop. Depends on layers 1–3 running.

- In → out: audience reactions → reweighted lineages → better content.
- Reward sources, innermost first: pogtown HAHA/CLAP events, frozen eval
  scores, YouTube Analytics (views, retention, CTR — read-only).
- Corpus (pinned): `jacob-burgess/killtony` @ `8f64531` at
  `/home/ubuntu/killtony-upstream` for style reference + frozen eval;
  `/home/ubuntu/killella/data` style profiles and prompt experiments as
  prior art.
- Judges (the Jev-shaped core): `funny` Score per draft vs rubric,
  `lands_for_family` Noul per decision family, `lineage` Choice,
  `promote` Noul with eval + reward facts in state. Composite scoring
  weights owned in code. Genetic operators (mutate premise, cross
  voice × face) propose; judges + frozen eval + audience reward dispose.
  Optimizer proposes, never self-promotes.
- Lens: lineage board (weights, support, Brier/ECE per family) + watch
  view (clips, reaction buttons as event emitters).
- QP: reward events appended as evidence, reweighting emits receipts,
  lineage promotion is a receipt or it doesn't happen. Reputation derives
  from verified runs under a tree head.

## Dependency DAG

Layer 0 → Layer 1 → Layer 2 → Layer 3 → Layer 4, with Layer 0 hardening
alongside throughout (TEE connectors land when they land). Each product is
one passport shape plus its connectors plus one lens. No product may
reimplement another layer's internals; bundles, events, and receipts cross
boundaries, nothing else.

## Expansion matrix (how we grow without new systems)

- New passports: trend-spawn, merch drop, collab episode, live room night.
  Same engine, new resource chain.
- New connectors: registrar #4, new social, new renderer, new analytics
  source. Port first, edits in `core/` only, contract tests each.
- New judges: one narrow question at a time, labeled set first, thresholds
  per consequence, versioned with the policy that uses them.
- New lenses: one tab, one job — run, evidence root, receipt, approve-deny.

## Jev integration (cross-cutting judge provider)

From the Refix quickstart and the awesome-jev collection, the usage is:

- Key handling: `TYPESAFE_API_KEY` deposited via the vault sidebar as
  `llm-inference`, resolved through capability grants, server-side only.
  Never in tree or browser. One more row in the capability matrix next to
  the zen provider and TEE inference.
- SDK: `@typesafe-ai/sdk` (Node 20+) or `typesafe-sdk` (Python), model
  `jev-latest` while exploring, pinned versioned id before anything
  production. Log the returned model field with every decision.
- Call shape: `systemOne({model, state, questions})` with `choice`,
  `score`, `noul`. Parallel questions per request over the same state;
  sequential calls where step two depends on step one. Arithmetic, dates,
  auth, and side effects stay in code — Jev gets semantic judgments only.
- First workloads, in order: queue triage (intent Choice, urgency Score,
  needs-human Noul — the ticket router verbatim), guardrail Nouls on
  untrusted email/DM/voice feeding quarantine next to the regex screen,
  comedy judges (funny Score, lands Noul, lineage Choice), composite
  lineage scoring with code-owned weights.
- Eval discipline per the collection: labeled sets from our own tasks and
  jokes, report false automation separately from unnecessary review,
  per-action thresholds, `other/review` outcomes always offered, store
  full distributions for Brier/ECE calibration, re-run eval before any
  model move (alias moves are gate changes: new id, new receipt).
- Useful patterns lifted: confidence-gated routing with human fallback,
  abstaining moderation, agent-trace observability on our own runs,
  autoresearch-style feature discovery for semantic ML features, and the
  jev-mcp shape (typed verification tools for agents) when our MCP grows
  past read-only.
- Honest limits: early access, text only, vendor speed and price claims
  unbenchmarked on our data. Everything above works with structured-output
  judges today; Jev slots in as a faster cheaper judge provider behind the
  same question contracts.

## QP continuity (the thread through every layer)

- One equation, one receipt shape, one store discipline at every layer.
- Gates versioned and content-addressed; a changed question or threshold
  is a new gate id, old receipts settle against old ids forever.
- Missing data is UNKNOWN at every layer: unmapped handle, undelivered
  video, unwatched clip — never FALSE, never zero.
- Grants precede spend and external consequence at every layer; fail
  closed; idempotency persisted before acting.
- No self-promotion at every layer: lineages, models, judges, and the
  optimizer itself advance by receipt or not at all.
