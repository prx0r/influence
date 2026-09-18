# Money proof — the mathematical core the vision depends on

The bigger the vision (stores, merch, agent earnings, cross-product
money), the less negotiable this is: every consequential money move must
be a cryptographic proof, not a log line. This is qprivately law applied
to value, and it is what lets WorkerKit runs and moltwork payouts compose
with socials and stores instead of trusting each other.

## The one money equation

No spend, listing change, payout, or inventory mutation is canonical
unless: exact bounded grant (payload hash, subject, expiry, single use,
max amount) → journal-before-act with idempotency key → effect →
independent readback (provider statement, not our request) → receipt with
all gates passing. Attempt evidence never settles a money claim. Timeout
or ambiguity settles to UNKNOWN and reconciles, never to success.

## What gets proven (each is a claim family with gates)

- Spend: grant authorized this exact amount to this exact destination for
  this exact purpose, readback shows it moved, budget still holds.
- Listings: title, price, and inventory on the platform match the desired
  state byte-for-byte at readback time; drift beyond tolerance opens a
  task, never silently edits.
- Orders: payment observed (amount, confirmations, invoice binding) before
  capability or fulfillment is minted — exactly once per invoice, no
  double-credit on duplicate callbacks, deterministic under/overpayment
  policy.
- Payouts: earnings split per the frozen policy hash, each leg a separate
  granted effect with its own readback.
- Refunds and chargebacks: provider readback ingested as evidence that can
  flip a settled claim through a new receipt — history appends, never rewrites.

## WorkerKit tie-in

WorkerKit is the execution plane: agents do real work, real outcomes emit
receipts (per the A-COM architecture). Money-proof is what makes those
receipts worth paying on. A run receipt plus a spend grant plus a readback
is a payable invoice an agent can present anywhere — including moltwork —
without anyone trusting the agent's word. The run log becomes the resume:
verified completed runs, false/unknown rates, spend reconciliation
accuracy, all derived from included receipts under a tree head, never a
stored score.

## Moltwork tie-in

moltwork.com is the work surface where autonomous agents make money. With
money-proof underneath, the composition clicks: agents arrive with socials
and endpoints from setup.social, take work through bounded grants, execute
as WorkerKit runs, get paid per proven outcome, and spend through the same
grant rails on stores, merch, and ads. Socials give them distribution;
money-proof gives them a bankable history. Anonymous operator, accountable
asset — the pmail identity-free branch covers setup, receipts cover
everything after.

## Hiring: the same primitive pointed at work

A hire is a bounded grant with acceptance gates attached: scope, max
spend, expiry, and the exact conditions under which payout unlocks —
deliverable hash matches, frozen eval passes, readback confirms. The
agent works as WorkerKit runs emitting receipts; payout fires only when
the acceptance receipt settles. Disputes are new receipts with
counter-evidence, never edits to old ones. This works identically for
human freelancers, outside agents via guest-bookings, and our own
subagents — one hiring rail, every engagement payable, provable, and
bounded. Reputation accrues to whoever did the work, keyed to verified
runs, portable to the next hire anywhere.

## Ordering (business before vision)

Vision without this core is a liability machine: unproven spend at
influencer scale is how you lose real money fast. So the money gates land
before the storefronts open: spend family first, then listings, then
orders, then payouts — each with grant checks, readback connectors, and
red-team tests asserting what must not happen (double-mint, drift-silence,
attempt-as-proof, grant replay). Stores open on top of green money gates.
