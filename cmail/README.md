# cmail — studio-wide communication bus

Fork-style build of `cloudflare/agentic-inbox` + multi-domain admin from AgentMail.mx.

```
Internet → Email Routing (catch-all) → Worker → Mailbox DO (SQLite) + D1 index + R2 raw
Web UI (/ui) + MCP (/mcp) on top. Drafts default; sends need explicit confirm.
```

## Live status (2026-09-10)

- Worker: `https://cmail.tradesprior.workers.dev` (deployed)
- D1 `cmail-index` (1a2b7b3e…), R2 `cmail-raw`, KV SESSION — all provisioned
- Steve bridge: `https://steve.intelligentothers.xyz` (named tunnel `steve-bridge`)
  → local steve on :35433 → `POST /api/observations/email` → HumanAction queue
- E2E verified: ingest → Workers AI classify → D1 → webhook → steve action
- Pilot inbound NOT yet cut over: `intelligentothers.xyz` root MX still Zoho
  (deliberate). Cut over one domain via Email Routing → `cmail` worker when ready.

## Setup (one unimportant domain first — no flag day)

1. `npm i && npx tsc --noEmit`
2. `wrangler d1 create cmail-index` → paste id into wrangler.toml
3. `wrangler r2 bucket create cmail-raw && wrangler kv namespace create SESSION`
4. `wrangler deploy` (paused — no email routing yet)
5. Cloudflare dashboard → Email Routing → route one test domain to this worker
6. Verify inbound/threading/attachments, then migrate more domains
7. Outbound: enable Workers Paid ($5/mo, 3k sends incl.) → uncomment `send_email` binding

## Zoho migration (adapter, not flag day)

Zoho Mail REST API supports message fetch/search/threads/send/drafts — build a
temporary sync adapter: Zoho → cmail D1/R2, new mail lands natively. Export
history via Zoho API into `email/raw/{domain}/...` + D1 rows.

## Security

Email = untrusted input. Parser → classification → agent → permission policy → tool.
Levels: READ DRAFT SEND INTERNAL_ACTION EXTERNAL_ACTION FINANCIAL_ACTION ADMIN.
Auto-draft only; `email.send` requires `confirmed:true`.

## Secrets

Never hardcode. Cloudflare token/account in agent-vault (`oracle` vault:
CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, R2 keys). Use `agent-vault vault run`.
