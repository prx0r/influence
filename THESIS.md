# Influence — thesis

Date: 2026-09-18. Living doc. cmail fork at 583cd62, origin removed so dash work in cmail never collides.

## What this is

Influence is the backend flow and management plane for AI influencers, built on the cmail graph. One system, two chains, dashboard-first, one purpose-built view at a time.

## Spine: the dependency graph

The pristine core is Project with a passport of desired resources. Connectors observe each kind and optionally apply. Reconcile writes ResourceState and emits HumanActions. Autopilot runs observe-act-verify for AUTO-safe work. RunLog receipts everything. Tradie jobs and influencer runs are passport shapes on the same graph, never the core.

Reference influencer run: mine a concept into candidates, map handles across socials and packages, score, verify domain with DNS plus RDAP, compare registrars, prepare-approve-register-wire with drift and budget guards, zone to NS, Email Routing into the bus, mailboxes live, project plus kernel plus reconcile, number via bridges, social verify, publisher as content calendar. Human confirms spend and sends at every autonomy level. Quarantine downgrades only.

## Two chains

Private chain holds what must stay secret: raw evidence, numbers, addresses, message bodies, effect journal with idempotency keys, encrypted and operator-scoped. Public chain holds only commitments: evidence roots, receipt hashes, signed tree heads, disclosure manifests with PII scanned out. Nothing sensitive crosses. Everything public is anchored to something private and checkable.

qprivately is law: gates and the transition equation, accepted only when all gates pass. qp is judge: tiny deterministic kernel replaying claim plus evidence to a verdict. Influence is the first workload that earns its history. Reputation derives from verified runs under a tree head, never from a score column.

Borrowed from pmail, in order: actuality TRUE/FALSE/UNKNOWN with false dominating unknown dominating true so timeouts never become false success; attempt evidence never settling claims, only independent readback via nonce roundtrips or confirmations; exact authority grants with payload hash, subject binding, expiry, single use, revocation under signature; effect journal with idempotency persisted before acting; privacy as code with compose, max-class policy, forbidden traits, identity surfaces; domain-separated Merkle evidence with public-commitment receipts; envelope/extension receipt split with external trusted-signer resolution; capability token hashes with derived credit ledger and exactly-once mint; per-direction bridge capabilities with lifecycle and hard-filter selection; MCP that advertises only what it can dispatch with bootstrap/read/consequential classes; red-team tests asserting what must not happen.

## Dashboard-first, human tasks at the center

The ideal flow is human-task centered, not feed centered. Task carries class and consequence, options as digits, recommendation, risk and cost of wait, proof-of-attempt requirements, dependencies, expiry, prediction and resolution refs, never secrets. Only low-risk local preference may climb toward auto. Authorization, secret, identity, physical and ambiguity stay human always.

Present-before-decide with prediction banked before display. The controller presents, the model predicts the operator action and banks the hash, only then the human answers with a digit plus optional artifacts through a sealed channel. Calibration measured on support, accuracy, Brier and ECE per decision family, climbing human through shadow and suggest to guarded and auto-eligible, with auto-eligible never meaning authorized. Grants precede spend, QP settles, Harbor stays eval-only with rewards imported as evidence.

The qpbot dashboard shell is the start: chat left with task rail right, token gate, loopback plus tunnel, stdlib only. AgentDeck gives the design language: calm by default with urgent on demand, glanceable sessions, type as instrument, hardware constraints celebrated. RSI is the post-hoc optimizer over runs feeding the bank; HLoop is the pre-decision predictor. Both stay.

## Dashboards: lightweight HTML, one purpose at a time

HTML is the ideal site for this: hero task card, queues by unblock value, runs with budget and approval, grants and receipts, log tails, reconcile states, all over polling or SSE on the same endpoints MCP uses. What HTML does not do — scaled realtime sockets, heavy drag planning, offline push, in-page signing, bulk files, hardware surfaces — stays with the daemon, server or native companion.

So various dashboards, designed one at a time, each for one purpose, staying flexible. One shell with lenses over the same queue rather than forks that drift: influencer ops with names and posts and inbox, money and grants, verification with receipts and tree heads, learning with calibration and RSI. Same task IDs everywhere.

Rendering is a first-class lens. Backends compute — kaggle jobs, mxth specimens, reconciles — and dashboards display. The mxth-style dash the other agent is building in cmail is the pattern: backend owns truth and audit, the page is a thin approval and render remote. New render needs start as one tab with one job: show the run, its evidence root, its receipt, its approve-deny.

## Working rules

Additive changes to live surfaces, never rename or remove a route or tool. Drafts everywhere, sends and spends behind tokens plus task approval. Secrets in vaults and env, never in tree, secret-scan before push. Actuality over booleans. Attempt is not observation. Human approval is not QP authority. Small diffs, verified before claimed.
