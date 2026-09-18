# Cloudflare-native hosting — decision record

Yes: Cloudflare-native is the correct stack for this vision. Reasons:
domains, DNS, Email Routing, and R2 already live in our account; Workers
put reads at the edge next to every door; Tunnel keeps the Python brain on
the VPS with zero inbound ports; R2 holds evidence blobs and backups with
no server to babysit.

## Split (final)

- Edge (Workers): static dash shell + read APIs (`/api/state`,
  `/api/health`, MCP reads) via cacheable fetches. Deploys with wrangler
  through vault-run so tokens never touch disk or tree.
- Brain (VPS, loopback only): reconcile, decide gate, vault, spend ledger,
  receipt log. Reached publicly only through the `influence-dash` named
  tunnel today; Workers-to-brain proxy when the edge worker lands.
- Data: SQLite on VPS as the working store; R2 as the evidence + backup
  tier (`scripts/r2-backup.py` nightly: receipts, rewards, drafts,
  quarantine logs, DB snapshots + manifest with sha256). D1 mirror for
  edge reads is Phase 4, not now.
- Mail: Email Routing into the bus; MailChannels on roast.pet stays.
- Secrets: agent-vault `oracle`/`cloudflare` vaults + env files. Nothing
  secret in any repo, on any edge, or in any chat.

## What this todo proved live

First R2 backup run completed (see command below for the repeatable form).
`R2_BUCKET` defaults to `influence-backups`; endpoint and keys come from
vault env at run time and are never printed.

```bash
export R2_ENDPOINT="$(agent-vault vault credential get CLOUDFLARE_R2_ENDPOINT --vault oracle)"
export R2_ACCESS_KEY_ID="$(agent-vault vault credential get R2_ACCESS_KEY_ID --vault cloudflare)"
export R2_SECRET_ACCESS_KEY="$(agent-vault vault credential get R2_SECRET_ACCESS_KEY --vault cloudflare)"
python3 scripts/r2-backup.py   # prints file names + bytes only
```
