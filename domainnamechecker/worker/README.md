# Domain Intelligence Engine — Cloudflare Workers

## Deploy

```bash
cd worker
npm install
npx wrangler deploy
```

## Endpoints

- `/` — Landing page
- `/api/health` — Health check
- `/api/verify/:domain` — Verify domain (DNS + RDAP)
- `/api/registrar/:domain` — Compare registrar prices
- `/api/mine` — Mine domains (POST, full pipeline)
- `/mcp` — MCP endpoint (JSON-RPC: tools/list, tools/call)
- `/llms.txt` — Agent discovery

## MCP Tools

- `verify_domain` — Full verification pipeline: DNS + RDAP
- `generate_domains` — Generate domain candidates from concept
- `score_domain` — Score domain by semantic meaning
- `compare_registrars` — Compare registrar prices
- `mine_domains` — Full pipeline: generate + verify + score + compare
- `get_analytics` — Search and click analytics
