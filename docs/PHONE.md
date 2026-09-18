# Phone — numbers without lying about identity

## The policy (from pmail, enforced by the `number` connector)

Three bridge classes, hard-filtered, never silently downgraded:

- ANON_CORE — no identity surface. Nothing in our stack meets this for PSTN.
- PSEUDONYMOUS_BRIDGE — no KYC, capability-gated (the only acceptable max).
- IDENTITY_BRIDGED — Telnyx and friends: full PSTN, full KYC. The machine
  must reject these under standard policy and say why.

A recorded number without live readback stays UNKNOWN, never READY.

## The Telnyx pattern (cmail reference, reimplemented on demand)

`cmail/stevejobless/stevejobless/telephony.py` owns the account side:
search available numbers by country, list owned numbers, point Call Control
webhooks at the brain, normalize inbound SMS/call webhooks to brain events,
send SMS with real delivery once creds exist. Without creds every call
degrades to stubs, so the flow is testable today.

Vault layout (platform `telnyx`, when the human wires it): `api_key`,
`connection_id` (call control app), `phone_number`, `messaging_profile_id`.
Secrets in vault/env only. SMS confirmations and call-to-job intake are
the two flows that matter; everything else is admin.

## What to do today (no creds)

1. Chat `setup` (or open the pipeline view): number row shows eligible vs
   rejected bridges with reasons — that IS the phone state.
2. Human buys a number out-of-band (Telnyx, orExperimental pikasim path
   only after live acceptance), seals `TELNYX_*` into the vault.
3. Reconcile: with creds present and readback confirmed, the row can go
   READY. Until then it stays UNKNOWN and says so.
