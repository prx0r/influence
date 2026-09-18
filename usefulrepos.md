# Useful repos — what each holds, what hiring+receipts still needs

Verdicts per repo against the full hiring+receipts loop (grant → work →
readback → receipt → payout → reputation). Statuses: COVERED (same
protocol already), ADAPTER (consume through a boundary, never fork),
TODO (gap to close), SOURCE (reference or corpus, not runtime).

## pq — live experiments (`/home/ubuntu/pq`) — ADAPTER

Real-API testing of the qpbot stack: vault resolution under pressure with
failover, arena tools, ledger chain verification, QP proofs against live
whale-feed/ETH/FOMO data, LLM harness runs — all logged to `runs/`, every
finding receipted. Tests: arena deep, htask harness, live LLM, missions,
onchain tools, privacy deep, production authority + privacy, RSI, vault deep.

- Keeps: the live-fire discipline. New influence connectors earn their
  place the pq way — real provider, real readback, receipt, or it stays stub.
- TODO: point one pq-style live test at each new connector (registrar,
  mailbox, bridges, publisher, YouTube read-back). No new harness needed.

## xmrecon — autonomous redteam sim (`/home/ubuntu/xmrecon`) — ADAPTER

CTF arena where agents capture targets: server-side verifier, hash-bound
flag comparison, append-only ledger in qp Store shape, campaign controller
(queue → allocate → run → outcome), tournament, guards with fail-closed
tools and human approval for high-risk class, deliberately-broken exploits
that MUST fail. Same shape as the kernel, explicitly not a fork.

- Keeps: anti-cheat testing pattern for hiring — deliberately-failing
  exploits become deliberately-failing grant abuses (replay, over-spend,
  forged readback) in our red-team suite. Tournament shape previews
  lineage competition for funnylab.
- TODO: port the must-fail fixture idea into influence tests; consume
  campaign outcomes as events, never reimplement the arena.

## monero-mcp — agent XMR wallet (`/home/ubuntu/monero-mcp`) — ADAPTER

MCP server giving any agent a private Monero wallet: balances, transfers,
address management across 12 tools. The XMR-bot leg: private money with
privacy-by-default so agent strategies can't be reverse-engineered
on-chain. Pairs with the private-attestation story — attested run on one
side (NanoGPT/Phala per `pdash/docs`), untraceable settlement on the
other.

- Keeps: wallet RPC as the money rail behind `xmr.pay` and payouts. Our
  invoice lifecycle (fresh subaddress per invoice, confirmation policy,
  exactly-once mint, deterministic partial/overpayment) sits on top; the
  repo owns key handling and chain I/O.
- TODO: confirmation-policy readback connector, split receive/spend
  wallets, payout legs as separate granted effects. No wallet crypto of
  our own, ever.

## qprivately + qpfinal — law + discipline — COVERED

SPEC, 7 objects, transition equation, receipts, 15 invariants; plus
processors-propose, HLoop, Harbor-eval-only, tournament promotion. This is
the protocol everything else must speak. Nothing here to rebuild.

## pmail — identity-free setup + proof semantics — COVERED/ADAPTER

Privacy composition, capability mint, exact grants, journal-before-act,
per-direction bridges, MCP advertise-only-dispatchable. Port patterns,
don't fork the runtime. The identity-free hiring path (anonymous operator,
accountable asset) comes from here.

## pdash — private dashboard reference — ADAPTER

NanoGPT/Phala TEE docs plus attestation flows, private chat shape, audit
discipline. Consume attestation checks as a connector; keep provider docs
as the reference.

## cmail + stevejobless — comms bus + tradie brain — ADAPTER

Email bus, drafts queue, quarantine screen, job pipeline, registrar
providers, desk. Source of connector patterns and the additive-to-live
rule. Port connector by connector.

## qpbot — agent runtime + Pi harness — ADAPTER

Pi sessions, subagent spawn/monitor/audit, missions, vault-scoped keys.
The worker layer to port for driving queues. Chat stays out of the kernel.

## pogtown / freaktown / killella — stage + game + analysis — ADAPTER

Game truth, avatar pipeline, Ella judge, style profiles, prompt
experiments. Bundles and events cross; internals never do.

## killtony-upstream — corpus — SOURCE

Pinned at `8f64531`. Schema reference + frozen eval material. Never a
runtime dependency.

## etsysignal — roast factory — ADAPTER

Order → beats → bundle → portrait → gift URL, live in-repo. Influence
wraps it with queue, grants, receipts. Venue boundary holds.

## agentcom lineage — no `/agentcomfinal` dir found

Closest: `qpfinal` (curated canonical tree), `agentcom_unpacked`,
`agentcomzips`, `agentseolab`, `finalbuilds2`. qpfinal is the reference;
the rest are archive. If `agentcomfinal` means something specific, point
me at it and I'll fold it in.

## Do we cover full hiring+receipts?

Almost — one protocol, four gaps, all named: live-fire connector tests
(pq pattern), must-fail grant-abuse fixtures (xmrecon pattern), wallet
readback + split wallets (monero-mcp), TEE attest connector (pdash).
Close those and any hire, anywhere, settles the same way. Extensibility
rule holds throughout: new repos arrive as connectors, judges, or stages
behind existing contracts — never as second kernels, second queues, or
second receipt formats.
