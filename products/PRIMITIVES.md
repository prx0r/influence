# PRIMITIVES — skip to the end: every product, exactly what it needs

One system, one law (`law/acom` @ c18433a), sixteen products. Each product
is a path through the dependency graph plus the primitives it settles with.
`gates_live` exist and run today; `gates_future` are named so promotion can
arrive as new gate ids, never edits. Machine-readable twin:
`products/primitives.json` (served by `product.get`, asked by chat
`primitives <name>`).

## The shared floor (every product stands on this)

Objects: CLAIM, EVIDENCE, TASK, RUN, GATE (+ GRANT where effects exist).
Receipt: TransitionReceipt, content-hashed id, FAIL first-class.
Store: append-only JSONL, hash-chained, `verify_chain` + per-receipt settle.
Base gates, live: `evidence-fresh-v1`, `no-duplicate-v1`,
`claim-resolved-v1` (+ `two-sources-v1` where corroboration matters).

## The map

- **setup.social** (infra, partial) — L1→L2→endpoint. Connectors live:
  names, domain, registrar, zone, website, social. Stub: mail, number,
  zone-apply. Grants: human task approval; spend grants with BUY-DOMAIN.
- **instant-influencer** (surface, partial) — setup.social → drafts → L5.
  Same connectors. First leaf that ends at an endpoint.
- **private-studio** (infra, partial, proof level 6) — L0 privacy +
  tee.attest + pmail subgraph (bounded exact grants, split wallets,
  commitments public / raw private). Stub: TEE chain validation, xmr.pay.
- **eval-api** (infra, partial) — L5 judges as metered endpoint. Judges
  live as rule-based v0 (intent, urgency, risk, funny); metered endpoint +
  capability mint are stub.
- **funnylab** (infra, designed) — corpus → sets → funny.score/lands →
  rsi.reweight. Needs frozen eval cut + one lineage. No gates, no moat,
  no effects by construction.
- **influencer-ops** (surface, designed, level 6) — L2+L4+L5, delivery
  settles on readback. Publisher/inbox observe live; sends stay gated.
- **influencer-studio / freaktown-autopilot / watch-loop / clip-farm /
  roast-line** (designed) — the content factory family. Freaktown stays
  whole until its factory split; the bridge pattern is one sealed import
  + one receipted job (see `products/influencer-studio.md`).
- **roast.pet** (surface, partial) — pipeline proven in etsysignal;
  here: order queue + first receipted roast are the missing receipts.
- **party-rooms / guest-bookings** (designed) — L7 rooms → events;
  pogtown adapter + booking passports outstanding.
- **storefront** (surface, designed, level 6) — listings → orders →
  fulfillment → payout, money-proof gates (spend-ledger pattern) before
  doors open.
- **trend-radar** (infra, designed) — one source connector + one lens
  away from live.

## How a product graduates

designed → partial → live happens receipt by receipt: gate ids registered,
connector observed honestly, FAIL receipts clickable in dash, chain green.
Promotion is a receipt or it didn't happen — optimizers, judges, and docs
never promote by themselves.
