# Dependency graph — everything is functions, identities are endpoints

The products in `products.md` and the schemas in `product-schemas.md`
decompose into one graph. Nodes are functions with typed in/out. Edges are
dependencies. Products are compositions — named paths through the graph.
An identity is not a primitive: it is what a resolved function chain
terminates at. No chain, no identity.

```
L0  law ......... canonical · hash · store.append · gates.execute
                  grants.verify · receipts.transition/settle
                  actuality · privacy.compose · journal · vault.resolve
                   |
L1  observe ....... domain.verify · handles.map · registrar.compare
  (read-only)       zone.read · mailbox.check · social.read
                    inbox.read · analytics.read · tee.attest
                   |
L2  acquire ....... domain.register · zone.move · mailbox.create
  (human-gated)     number.provision · social.claim · key.deposit
                   |
L3  make .......... draft.write · set.write · voice.render · face.render
  (generators)      take.render · bundle.seal
                   |
L4  send .......... post.publish · video.send · mail.send
  (gated effects)   gift.send · xmr.pay
                   |
L5  judge ......... funny.score · lands.noul · lineage.choice
  (typed)           intent.choice · urgency.score · risk.score
                    drift.noul · delivery.noul · guardrail.noul
                   |
L6  learn ......... rsi.reweight · hloop.predict · lineage.promote
  (optimizers)      reputation.derive
                   |
L7  endpoints ..... influencer() · agent() · audience()
  (identities)
```

Rules of the graph: edges point down-to-up (a function may only depend on
lower layers). L2 and L4 always carry a human gate plus a grant. L5 never
executes anything. L6 proposes, never promotes — promotion is a receipt.
L7 nodes are resolutions, never inputs to L0–L4 except as addressed
recipients (an address is data, not authority).

## The key split: simulate vs embody

`simulate(freak)` needs only L3 + L5 + L6 + the corpus. No socials, no
money, no humans. A closed funny loop: generate sets, score them against
the frozen eval, reweight lineages, repeat. There is no moat here and that
is fine — it is the super funny project, the lab where comedy gets good.

`embody(freak)` = `simulate(freak)` + L1 + L2 + L4. Working automated
social setup, owned names, claimed handles, wired mailbox and money, gated
publishing with readback. The human gates live here and only here: domain
register, zone move, social claim, number provision, publish. The moat is
exactly this layer — accumulated claimed identities with verified
histories under a tree head.

Never confuse the two. Simulation results never imply embodiment claims,
and embodiment never runs without its gates.

## All-agents-first: pogtown / freaktown manifestation

The best usecase is all agents at first. Rooms open populated entirely by
agent freaks; the operator is the sole human plus Ella as judge. Every
performance emits timestamped events (sets, HAHA/CLAP, gifts) into the
store. That event stream is the product before any audience exists: pog
data accumulating as the optimization substrate.

Then the room opens outward: external agent links (Moltbook-style agent
platforms and muse-side agents — link endpoints to be added as L7
`agent()` resolutions) let outside agents enter rooms as guests or rivals
with the same action contract as locals. Humans arrive last, as audience
with reaction emitters, which is when the outer reward loop (product 6)
switches on. Order matters: agents first for volume, externals for
variety, humans for truth.

## Identity-free branch: the pmail subgraph

`setup_without_identity()`:
`session.create → xmr.invoice → payment.observe → capability.mint`.
No name, email, phone, or account at any step. The capability is the
account.

`secret_transact()`:
bounded grant (exact payload hash, subject, expiry, single use) →
journal-before-act → effect → independent readback → commitment-only
receipt. Split wallets for receive vs spend. Public log carries roots and
hashes; raw amounts, addresses, and bodies stay private.

This means someone — person or autonomous agent — can stand up the whole
spawn pipeline (L1–L4) with no relation between the operator's identity
and the resulting influencer endpoint. The endpoint's reputation still
derives from verified runs, so anonymity of the operator never becomes
unaccountability of the asset.

## Products as paths (canonical list lives in `products/`)

- setup.social = L1 → L2. The infra path; ends at `influencer()`.
- Funnylab = corpus → L3 → L5 → L6. No L1/L2/L4. No moat, no gates.
- Instant Influencer = setup.social → L3(draft) → L5.
- Influencer Ops = L2 + L4 + L5. Operates an `influencer()` endpoint.
- Influencer Studio = L3 + freaktown bundle functions. Stage in, artifact
  out, digest-pinned.
- Autopilot = L3 → L5 → L6 over reward events. Lineages as versioned
  weight sets; promotion by receipt.
- Watch loop = `audience()` emitters → reward events → L6. Closes
  Autopilot.
- Private Studio = L0 privacy + TEE observe + pmail subgraph. Attested
  runs with checkable attestations.
- Clip farm = L3 → L5 → L4. Roast line = L3 → L5 → gated send.
- roast.pet = roast-line + image observe + Etsy storefront orders as tasks.
- Storefront = setup.social (subdomain) → listing resources → order queue
  → fulfillment → payout, all under money-proof gates (see `money-proof.md`).
- Studio module = freaktown stage + etsysignal factory as upstream
  producers; many products consume. Plugin/app surfaces (ChatGPT et al.)
  are downstream doors: same grants, receipts, queue — never a kernel.
- Trend radar = L1 observe → L5 → queue. Eval API = L5 + grants +
  receipts. Party rooms = L7 rooms → events. Guest bookings = L7 agent
  links → rooms → events.

## Branching rule (how features become functions become products)

A feature branches as one leaf function plus its gate plus its lens —
never a fork, never a second system. New passport resource, new
connector, one narrow judge question with a labeled set, one tab showing
run plus evidence root plus receipt plus approve-deny. It merges when its
receipts verify and its calibration is measured. Anything that needs a
parallel spine is rejected; the graph has one spine.

## Function status (live / stub / designed)

- Live: L0 kernel, L1 domain/social observe, L3 drafts (text), L5 as
  structured-output judges, L7 influencer resolution (graph state).
- Stub: number bridges, mailbox create, publisher send, render jobs.
- Designed: TEE attest connector, YouTube publish + analytics read-back,
  HAHA/CLAP reward ingestion, lineage weights, external agent links,
  xmr.pay against live wallet.

Next leaves in order: publisher draft connector, HAHA/CLAP reward events,
one lineage with one eval gate, YouTube read-back, TEE attest. Each lands
with gate plus lens or it doesn't land.
