# Buy a domain — check → prepare → approve → register → wire

Nobody — no agent, no script — buys without a human confirming spend once.
The machine below prepares everything so the confirm is one informed click.

```
1. check    checker prefilter + live registrar prices, cheapest first
2. prepare  fails closed on unavailable / over-budget (no side effects)
3. approve  human confirms → single-use approval token out (sha256-stored)
4. register rechecks availability + price drift (≤10%) fresh, then registers
5. wire     zone → NS → routing → mailbox, each step observed + receipted
```

Provider order: Cloudflare (at-cost, already home) → Porkbun → name.com.
Excluded TLDs short-circuit with the reason; Porkbun covers them, then the
NS moves to Cloudflare. Sandbox/fixture defaults everywhere until
`DOMAINS_ALLOW_LIVE=1` AND a valid approval token are both present —
either missing fails closed.

## Status in influence (2026-09-18)

Steps 1–2 run today via chat `check <domain>` (checker verify + registrar
compare, evidence attached). Steps 3–5 live in cmail's domain machine
(`stevejobless/stevejobless/domains.py` + `domain_routes.py`, runbook in
`cmail/docs/GUIDE.md`) and arrive here as the next leaf: approval tokens
already have their shape (single-use, sha256-stored — same as our task
approve path), and registration binds to the spend ledger's drift rule.
Until then: the machine hands you priced buy links and a prepare sheet,
you buy, it verifies and wires.

## Email receiving (same gate, different wire)

Inbound mail follows the identical pattern: observe (MX/DNS evidence) →
human flips Email Routing → machine verifies first receipt. The cmail bus
(Worker + MailboxDO + drafts queue) is the live reference; here the `mail`
connector holds desired-state and the runbook while provider wiring lands.
