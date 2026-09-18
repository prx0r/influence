# private-studio — kind: infra

TEE runs plus identity-free setup. Hardens everything without touching
any product's internals.

- Intent: private actions with checkable proof.
- In → out: request → attested run + commitment-only receipt.
- Path: L0 privacy + tee.attest + pmail subgraph (session → capability →
  bounded grant → journal → readback → receipt).
- Needs: TEE attest connector (NanoGPT / Phala per `pdash/docs`),
  xmr.pay against live wallet.
- Feeds: all products (private lane for any of them).
- Status: providers documented, types and gates live. Next: one
  connector, one lens, one attested turn end to end.
