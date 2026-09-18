# ARCHITECTURE

```text
name ──► checker worker ──► claim_kit ──► steve deals ──► registrar (CF→Porkbun→name.com)
                                                        │  auto cheapest under cap
                        ┌─── zone ──► NS ──► Email Routing ──► cmail worker ──┐
                        │                                                     │
                        │  MailboxDO (hot threads) + D1 (index) + R2 (raw)    │
                        │  classify → quarantine? → webhook → steve           │
                        │  /mcp: inbox/search/read/draft/send/archive/ask     │
                        │                                                     ▼
voice ──►┐         stevejobless (FastAPI + SQLite, systemd, tunnel)
Telnyx ──►├─► intake ──► jobs ──► quotes ──► slots ──► schedule ──► invoice ──► desk
WA/IG ──►┤         │  kernel per business (prefs/price/autonomy)              ▲
email ──►┘         │  feed (cross-business scoring) · reconcile · audit       │
                   └── drafts ──► cmail queue ──(Paid+SENDER)──► sends ──────┘
```

## Design decisions (load-bearing)

- **MailboxDO = hot state, D1 = searchable view, R2 = truth.** Never query 30 DOs for global questions.
- **Drafts everywhere, sends on confirm.** The worker can't send without Paid; the brain won't send without a human. Both must flip.
- **Approval tokens, not sessions**, for money. Single-use, hashed, drift-rechecked.
- **Quarantine downgrades only.** Injection screen runs before classify results are used; quarantined mail loses urgency, webhooks, and corpus membership.
- **Transcripts have a TTL.** 90-day sweep; metadata and stats live on.
- **Providers compete.** Domain auto-mode quotes all configured registrars, buys cheapest. Channels degrade to stubs with the next step printed, never dead ends.
- **One kernel file, two consumers.** Voice reads conversation fields, brain reads `tradie:`.

## Cloudflare-native surface

Registrar API · Email Routing/Service · Workers/DO/D1/R2 · Workers AI ·
Tunnel · Official MCP servers (bindings/docs/observability). Pinned references
in `cmail/docs/cloudflare/`. Live IDs in `cmail/wrangler.toml`; secrets in
agent-vault + root-only systemd drop-ins — never in this tree.
