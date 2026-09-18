# Products — what this stack can become

Living spec. Canonical per-product files live in `products/` (one schema
each, infra vs surface marked, dependency map in `products/README.md`).
This doc is the narrative; `products/` is the registry. Everything rides
the same spine: Project + passport, connectors observe / optionally
apply, reconcile writes state + tasks, receipts prove it, dash shows it.
If it isn't visible in the dash, it isn't a product yet.

## 0. Shared substrate (all products assume this)

- `qprivately` is law: transition equation, 7 objects, receipts, 15 invariants.
- `influence` graph: passports as the shape of any job, autopilot for
  AUTO-safe work only, human tasks with digit options at the center.
- Two chains: private holds secrets and raw evidence, public holds roots,
  receipt hashes, tree heads, disclosure manifests. Nothing sensitive crosses.
- Working rules hold everywhere: drafts everywhere, sends and spends behind
  tokens + task approval, secrets in vaults never in tree, attempt is not
  observation, human approval is not QP authority.

## 1. Private Studio (privacy narrative + TEE execution)

The privacy story, made executable. An operator gets a studio where the
agent works without ever holding their identity, and the private parts run
inside attested enclaves.

- Private chat and private actions via TEE runtimes: NanoGPT TEE
  (`nano-gpt.com/api`, attestation + per-response signatures) and Phala
  confidential AI (GPU TEE, Intel TDX, `aci_verified` routing). See
  `pdash/docs/private_compute/`. pdash is the reference dashboard for this:
  same shell, QP receipts on every action, sub-agents, audit, monitor.
- pmail supplies the semantics: ANON_CORE composition, identity surfaces,
  capability-matrix bridges, exact grants, journal-before-act, Merkle
  evidence with public-commitment receipts.
- What the user gets: a session funded without conventional identity, a
  capability not an account, private inference with attestation they can
  check, and receipts that prove what happened without leaking what was said.
- Dash lens: private-runs view — run, evidence root, receipt, attestation
  ref, approve-deny. Same task IDs as everything else.
- Status: pdash documents the providers; pmail has the types and gates;
  influence needs the TEE connector set (attestation check as a connector,
  receipt id pinned per response). Next: one connector, one lens, one
  attested chat turn end to end.

## 2. Instant Influencer (spawn from scratch)

The flagship flow: an agent whips up an influencer from nothing and hands
them socials plus identity. This is the multi-dashboard array at full power.

- Input: a concept or a trend pointer. Output: handle, domain owned,
  zone live, mailbox live, number provisioned via bridges, socials claimed,
  first-week content drafted. Every step is a passport resource with a
  connector behind it; missing pieces surface as human tasks with digits.
- Reference run already in THESIS: concept mining, handle mapping across
  socials and packages, scoring, domain verify DNS plus RDAP, registrar
  compare, prepare-approve-register-wire with drift and budget guards, zone,
  Email Routing into the bus, mailbox, number, social verify, publisher as
  content calendar.
- Dash lenses, one purpose at a time: names + handles, money + grants,
  verification with receipts and tree heads. One shell, same queue, no forks.
- Status: graph + dash + receipts live. Next: port remaining connectors
  (registrar compare, zone, mailbox, number bridges) as passport kinds.

## 3. Influencer Ops (manage + send)

The day-to-day after spawn: keep them alive, keep them posting, keep the
money straight.

- Content calendar via publisher/postiz (drafts only, publishing gated),
  inbox triage via needs-reply, deals and renewals with drift guards,
  domain renewals as desk actions, spend board with budgets and approve-deny.
- Video send-out: render jobs as connector resources (desired = spec,
  observed = artifact hash), delivery as a gated send behind human confirm.
  Attempt evidence never settles the claim; only readback (delivered +
  viewable) does.
- Status: design pinned in DEV_PLAN Phase 5. Next: publisher connector,
  inbox connector, one ops lens.

## 4. Influencer Studio (what do they create)

The content engine, linked with freaktown. Freaktown owns product and
stage: avatar pipeline (face profiles, VRM/GLB, takes, revoice, walkout),
voice bank, Ella as character and judge, performance contracts, delivery.
Pogtown owns game truth: rooms, gift packs, order state machine, the five
gift tools, media providers. Freak Pack is portable identity; renderers
borrow it, never own it.

- Influence holds the management plane: who the influencer is, what they
  own, what content is queued, what went out, what it earned. Freaktown
  holds the stage: how they look, sound, and perform.
- Boundary: bundles and events cross, never internals. Influence consumes
  freak bundles by digest; freaktown never reimplements the queue, and
  influence never reimplements the avatar pipeline.
- Status: both sides exist. Next: one sealed bundle import (digest-pinned),
  one content job from queue to stage to published artifact with receipt.

## 5. Freaktown Autopilot (the self-running show)

The big one: freaktown entirely automated. New freaks spawn from genetic
operators — mutate premises, cross voices with faces, select on audience
response — and the show runs itself with humans as audience and final gate.

- Spawning: the Instant Influencer flow (product 2) becomes the birth
  canal. A spawned freak is a passport that completed: identity, voice,
  face, premise, first set.
- Comedy corpus (pinned): `jacob-burgess/killtony` @ `8f64531`,
  persisted at `/home/ubuntu/killtony-upstream` — Bun/SST app with Drizzle
  schema over episodes, guests, sets, venues, videos, and transcripts
  chunked plus embedded (`transcript-chunk`, `transcript-embedding`,
  OpenAI embeddings). Gives a structured, searchable Kill Tony corpus:
  set structure, roast mechanics, crowd-work patterns. Prior art sits in
  `/home/ubuntu/killella/data`: style profiles with techniques
  (misdirection, escalation, callback, deadpan, wordplay), themes, top
  moments, plus prompt/script experiments. Corpus feeds draft generation
  and a frozen eval set that new material is scored against; it trains no
  production weights by itself.
- POG as the RL loop: pogtown already emits timestamped performance events
  with set-relative HAHA / CLAP reactions. Those reactions are the reward
  signal. Our RSI (post-hoc optimizer over runs, already in THESIS alongside
  HLoop the pre-decision predictor) reweights: which premises, voices,
  formats, and posting slots actually moved the room. Google's RSI research
  direction — agents improving agents from run histories — is the same
  shape; ours stays receipt-bound so the optimizer can propose but never
  self-promote.
- Judge side (JEV-shaped): humour needs a reward function, and scoring
  whether a bit landed is a checker-shaped typed decision, not a writing
  task. TypeSafe's Jev (System One, Sept 2026, RLCD — reinforcement
  learning for calibrated decisions) is built exactly for that: state in,
  typed score plus honest probability out, milliseconds, cheap. That maps
  directly onto our HLoop calibration demand (Brier/ECE per decision
  family): laugh-prediction and premise-ranking judges with calibrated
  confidence feeding the autonomy ladders. Early-access and unverified, so
  the move now is the architectural lesson with current models — typed
  structured-output judges, calibration measured — with a Jev-shaped
  provider slottable later as one more vault-held inference key.
- YouTube as the control function: publish gated sets, read back YouTube
  Analytics (views, retention,CTR by video — read-only API scope) as the
  outer reward loop, evolve what people actually watch. Publishing stays
  behind human approve + grant; analytics is evidence, never authority.
- Trend spawning + category optimization: mine trends into candidate
  freaks, run categories (roast, absurd, deadpan, musical) as separate
  lineages with their own weights, promote only through frozen eval plus
  audience reward. A candidate version never replaces the current one by
  assertion — same rule as qpfinal: promotion is a receipt or it doesn't
  exist.
- Status: freaktown stage + avatars live, pogtown game packs + reactions
  live, influence queue + receipts live, RSI/HLoop designed. Next: pin the
  corpus, wire HAHA/CLAP into the run log as reward events, one lineage
  with one eval gate, one YouTube read-back connector.

## 6. Watch + Earn loop (humans watch, system learns)

The audience side that closes product 5: humans watch the show (live room,
clips, YouTube), their reactions become reward, the system gets funnier,
reputation derives from verified runs under a tree head — never from a
score column.

- Same queue, new lens: watch view with clips, reaction buttons that emit
  events, calibration of predicted vs actual laughs per decision family.
- Money follows the same grants as everything else: gifts via pogtown
  packs, spend bounded, receipts on every consequential move.

## 7. Funnylab (the simulate-only loop)

The lab with no gates and no moat, and that is the point. Generate sets
against the pinned corpus, score them with typed judges and the frozen
eval, reweight lineages, repeat — for the price of inference. No socials,
no money, no humans in the loop. Simulation results never imply
embodiment claims; the lab's output is funnier lineages plus receipts,
and embodiment stays gated behind it.

- Function path: corpus → set.write → funny.score / lands Noul →
  rsi.reweight → lineage weights. See `dependency-graph.md`.
- Next: frozen eval set cut from the corpus, one lineage, first
  reweight receipt.

## 8. More products on the same graph

- Clip farm: cut sets into clips (render job with spec in, artifact hash
  out), score clip candidates, queue the winners for gated publish.
  Path: L3 → L5 → L4. Next: one cutter connector, one clip lens.
- Roast line: crowd-work as a service — submit a target, get a roast set
  back through the frozen eval plus human approve. Path: L3 → L5 → gated
  send. Next: roast rubric as Score criteria.
- Trend radar: mine trends into candidate freaks with evidence attached,
  ranked by composite score in code. Path: observe → judges → queue.
  Next: one trend source connector, one radar lens.
- Eval API: score-your-joke as a metered endpoint — typed scores plus
  calibration, receipts on every call. Turns our judges into someone
  else's infrastructure. Path: L5 + grants + receipts. Next: one
  endpoint with capability mint.
- Guest bookings: outside agents book stage time through the same action
  contract as locals, bounded by grants, settled by receipts. Path: L7
  agent links → rooms → events. Next: booking passport, one external
  guest end to end.

## Build order

Funnylab first (cheapest loop, feeds everything), spawn next (closest to
live), then ops (3), then the freaktown bundle bridge (4), then the
autopilot loop one lineage at a time (5), with the private studio (1)
hardening alongside as the TEE connectors land and the watch lens (6)
closing the loop. Clip farm, roast line, trend radar, eval API, and guest
bookings branch off once their parent layers run. Each product is one
passport shape plus its connectors plus one dash lens — never a new system.
