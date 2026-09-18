# cmail — the agentic business stack

**One name, owned everywhere, touched once. One business, run by agents, seen as one queue.**

Email, voice, WhatsApp, SMS, and socials converge into a job pipeline
(lead → quote → schedule → invoice) with drafts everywhere and human confirm
on every send. Untrusted input stays untrusted all the way down.

```text
name ──► checker ──► buy ──► zone ──► mail + business + number + socials
                                                         │
              voice ──►┐                                 ▼
           whatsapp ──►┤► brain (jobs/quotes/slots) ──► desk (one queue)
              email ──►┘
```

## Bring-up (fresh machine, 5 min)

```bash
git clone https://github.com/prx0r/cmail.git && cd cmail
# brain
cd stevejobless && python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]' && cp .env.example .env
python3 -m pytest tests/ -q        # 80+ pass, no keys needed
steve serve                        # → http://127.0.0.1:8787, desk at /desk
# email bus
cd ../cmail && npm install && npx tsc --noEmit && npm test
npx wrangler deploy                # after filling wrangler.toml IDs
# names
cd ../domainnamechecker/worker && npm install && npx wrangler deploy
```

Everything degrades gracefully without creds: sends stub, providers 409 with
the next step, slots fall back to scheduled-job blocks, quotes mark `tbd`.

## What's inside

| Dir | Role |
|---|---|
| `cmail/` | Cloudflare-native email bus: Worker + MailboxDO + D1 index + R2 raw, MCP-first, drafts queue, injection quarantine |
| `stevejobless/` | Business brain: kernels, jobs, quotes, slots, feed, invoices/VAT, channels, Telnyx/LiveKit/Google backends, domain deals, reconcile, desk |
| `domainnamechecker/` | Name intelligence: verify (DNS+RDAP), registrar compare, handle map (socials/packages/ENS), claim kits, MCP |
| `voiceagentfeedback/` | Review + contract + build list for the voice track (`prx0r/voiceagent`) |

## Documentation

- [`docs/GUIDE.md`](docs/GUIDE.md) — **start here**: operate the whole stack
- [`docs/RECIPES.md`](docs/RECIPES.md) — copy-paste runs: onboard, buy, intake, quote, invoice, backup
- [`docs/API.md`](docs/API.md) — endpoint reference (brain + bus + checker)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, flows, Cloudflare map
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model + enforced controls
- [`docs/REPRODUCE.md`](docs/REPRODUCE.md) — prove it all works, step by step
- [`docs/MCP.md`](docs/MCP.md) — future: one MCP to rule the stack
- [`HANDOVER.md`](HANDOVER.md) — live infra, open threads, next steps
- [`stevejobless/SKILL.md`](stevejobless/SKILL.md) — 15-min business onboarding
- [`stevejobless/NORTHSTAR.md`](stevejobless/NORTHSTAR.md) — the end-state loop
- `AGENTS.md` — binding rules for coding agents

## One-command health

```bash
curl -s https://cmail.tradesprior.workers.dev/api/stats
curl -s https://steve.intelligentothers.xyz/ -o /dev/null -w "%{http_code}\n"
curl -s https://domainnamechecker.tradesprior.workers.dev/api/health | head -c 120
```
