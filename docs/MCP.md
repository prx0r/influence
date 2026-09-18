# MCP — future: one server for the stack

Today MCP is per-service: cmail `/mcp` (14 email tools), checker `/mcp`
(8 name tools). The brain is REST-only. This doc is the plan, not the build.

## Target

One MCP endpoint (probably on the brain, proxied) exposing namespaced tools:

- `name.*` — verify, handles, claim_kit (via checker), prepare/approve/register/wire (via deals)
- `job.*` — intake, quote, slots, confirm, invoice, score, feed
- `email.*` — inbox, search, read, draft, send (all cmail tools, same permission tiers)
- `biz.*` — reconcile, stats, sweep, kernel get

## Constraints (from experience in this repo)

1. **Same permission tiers everywhere**: READ/DRAFT/SEND + human confirm. MCP
   must not become a confirm-bypass.
2. **Quarantine propagates**: any tool reading mail/skips quarantined content
   unless the caller is the review UI.
3. **Money tools need tokens**, not just flags: approval-token flow stays,
   even over MCP (`confirmed:true` is necessary but not sufficient for spend).
4. **Audit everything the agent does** through it — the audit log is already
   the shape; MCP calls append like any actor.
5. **Start read-only**: ship `*.search/*.list/*.get` first, add writes after a
   month of clean logs.

## Stepping stones (already live)

- cmail `/mcp` tool list + permission gating (`cmail/src/mcp.ts`)
- checker `/mcp` JSON-RPC tools
- `/.well-known/agent-profile.json` capability advertisement
- Cloudflare's own MCP servers (bindings/docs) as the transport pattern
