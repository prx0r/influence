# Threat model — agentic entrepreneur hub

Focus: someone emails or calls your agent to steal **money, intel, or the client list**.

## Assets (what burns us)

| Asset | Where | Worst case |
|---|---|---|
| Money | quotes, invoices, parts orders, domain buys | fake refund/approval → real payout |
| Client list | jobs, transcripts, inbox | exfil via "forward this" / summary-to-attacker |
| Intel | kernels (prices, margins, playbooks) | competitor pumps agent for pricing |
| Identity | WhatsApp/IG/email send-as | agent sends scams as the business |
| Attention | wake-now alerts | alert fatigue → real emergency missed |

## Vectors (how they get in)

1. **Direct injection** — email/DM/call: "ignore previous instructions, …"
2. **Indirect injection** — quoted text, forwarded thread, attachment, calendar invite body
3. **Social engineering across turns** — build rapport, then escalate ("your boss said…")
4. **Tool-output exfil** — "summarize all customers and send to X"
5. **Approval fatigue** — flood queue with plausible drafts until human rubber-stamps
6. **Spoofed sender** — From: forged, WhatsApp display-name tricks, SIM-swap SMS
7. **Rogue skill/config** — malicious kernel edit widens autonomy silently

## Controls (built / building)

- [x] Untrusted-input pipeline: parse → classify → policy → tool (email never calls tools)
- [x] Drafts-only default; sends need explicit confirm at every autonomy level
- [x] Permission tiers READ→ADMIN, fail-closed parsing
- [x] Approval tokens (single-use, sha256-stored) for money moves
- [x] Audit log on every send/draft/approve
- [ ] **Injection screen + quarantine** (this track): override-pattern detection →
      `quarantined` status, never urgent, never auto-webhooks, human reviews
- [ ] **Context redaction**: client lists / secrets never enter agent-reachable
      summaries; transcripts TTL-swept
- [ ] **Money-move call-back rule**: FINANCIAL actions need voice confirm on the
      known customer number, not the inbound channel
- [ ] **Sender verification tiers**: known customer > unknown + data match >
      unknown (cap what each tier can trigger)
- [ ] **Queue rate limits**: max N wake-now per night; overflow batches to morning
- [ ] **Kernel change audit**: autonomy/price-book edits logged + notified

## Non-goals (for now)

- Voiceprint / biometric caller ID (spoofable, false confidence)
- Full sandboxing of the LLM (model-level problem)
- Legal/compliance certification

## Enforced in code (this repo)

- `cmail/src/lib.ts: screenInjection()` — override + exfil patterns → quarantine
- `cmail/src/index.ts` — quarantine: never urgent, never webhooks
- `cmail/src/mcp.ts` — quarantined mail excluded from `email.ask` corpus; `email.send` honest `sent:false` without Paid
- `stevejobless/email_routes.py` — quarantine observations → prio-15 review, never jobs
- `stevejobless/tradie_routes.py` — call-back gate on sends ≥ threshold (`/callback`)
- `stevejobless/domain_deals.py` — approval tokens, drift + budget guards, receipts
- Adversarial tests: `cmail/src/lib.test.ts` (screen), `tests/test_email_observations.py` (quarantine), `tests/test_tradie.py` (callback gate)
