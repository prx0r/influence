# BOOTSTRAP — what a fresh agent (or box) needs to run this repo

This repo is fully operable from inside the studio environment. From a cold
clone elsewhere, work through this list top to bottom.

## 1. Read (5 min)

`AGENTS.md` (binding rules) → `THREADS.md` (pick an A-thread) →
`docs/GUIDE.md` + `docs/REPRODUCE.md` (verify like we do).

## 2. Runtimes

- Python 3.11+, `pip install -e 'stevejobless/.[dev]'` (needs `pyyaml`, `httpx`)
- Node 20+, `npm install` in `cmail/` and `domainnamechecker/worker/`
- `wrangler` CLI for worker deploys; `cloudflared` for tunnels

## 3. Secrets (never in the tree — all three required for live work)

| Secret | Source | Used for |
|---|---|---|
| `agent-vault` CLI + `oracle` vault | studio box only | CF + registrar + R2 + Gmail creds (never printed) |
| `/etc/stevejobless.service.d/*.conf` | root-only drop-ins | server env: DB path, CF tokens, bridge secrets |
| `GH_TOKEN` env | your own token | push (see `scripts/sync-push.sh`) |

Without these: suites still run (no keys needed), but live verify + deploys
are impossible. Say so loudly instead of faking receipts.

## 4. Services (systemd, studio box)

`stevejobless.service` (:35433) · `steve-tunnel.service` (public URL) ·
`steve-backup.timer` (nightly R2). Check: `systemctl is-active …`,
logs via `journalctl -u …`.

## 5. First verify (prove the checkout works)

```bash
cd stevejobless && .venv/bin/python -m pytest tests/ -q   # expect 80+
cd ../cmail && npx tsc --noEmit && npx vitest run          # expect 13
curl -s https://steve.intelligentothers.xyz/ -o /dev/null -w "%{http_code}\n"
```

## 6. Work loop

Pick topmost open A-thread in THREADS.md → build → test → live-verify →
`./scripts/sync-push.sh "message"` → move thread to Closed. Never edit
`/tmp/cmail-repo` subtrees directly — it re-syncs from `/root` on every push.
