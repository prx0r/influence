# qpbot ↔ influence MCP hookup

Influence exposes its dependency-graph flow as read-only MCP tools over
plain HTTP POST. No Pi changes needed: any qpbot worker, Pi extension, or
shell step calls it. Writes stay on REST behind the decide gate.

## Tools (read-only, can never spend/send/mutate)

`influencer.list`, `influencer.get`, `queue.list`, `graph.describe`,
`product.list`, `product.get`, `receipt.get` (with independent settle
verification). Full contracts in `dash/mcp.py`.

## Calling it

Same box, token from `dash/.token` (0600, never in tree or chat):

```bash
python3 scripts/mcp-call.py tools/list
python3 scripts/mcp-call.py tools/call queue.list '{}'
python3 scripts/mcp-call.py tools/call graph.describe '{}'
python3 scripts/mcp-call.py tools/call product.get '{"name":"funnylab"}'
```

Pi harness: wrap `scripts/mcp-call.py` as a custom tool (read-only set).
Recommended first workflow: `queue.list` → present task in dash →
human decides digit → worker reads back `influencer.get` to confirm.
Workers observe through MCP; humans authorize through the HTask rail;
QP receipts settle the rest.

## Rules

- MCP advertises only what it can dispatch; unknown tools error, never
  guess.
- Quarantine and vault values never enter tool results.
- Consequential actions go through REST (`/api/present` then
  `/api/decide` with the single-use prediction ref), never through MCP.
