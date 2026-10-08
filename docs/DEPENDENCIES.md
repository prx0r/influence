# DEPENDENCIES — every process, port, and secret (2026-10-08)

Single box. Everything below must be running for the full loop.
Restart recipes use `setsid nohup … &` so they survive shell exit.

## Processes & ports (loopback only; Cloudflare tunnels are the perimeter)

| Port | Process | What | Data dir | Restart |
|------|---------|------|----------|---------|
| 8793 | `influence/dash/server.py` (stevejobless venv) | agentcom.org dash + MCP + chat | `dash/influence.db` (WAL), `decisions.db` | `serve.sh` env¹ |
| 8794 | phone proxy | phone.agentcom.org SMS/calls | Telnyx webhooks | existing runner |
| 7777 | FableCut `server.js` (node22) | video timeline UI + REST/SSE | `/root/fablecut-data` (`FABLECUT_DATA_DIR`) | `node server.js` in `/root/fablecut` |
| 7778 | `photocraft-web/serve.js` (node22) | PhotoCraft WASM image editor (static + COOP/COEP for wasm threads) | none (stateless) | `node /root/photocraft-web/serve.js` |
| 3999 | xman Next dev | X scheduler (3 slots), approvals, Bridge API | `xman/var/*.sqlite` | `npm run dev` in `/root/xman` (node22!) |

¹ Dash env: `LIVE=1 DASH_PORT=8793 DASH_JOURNAL=dash/decisions.db
INFLUENCE_VAULT=dash/vault.json PHONE_AUTH_FILE=/root/stevejobless/.phone_auth`.

## Runtimes (pinned — system node is v26 and breaks native builds)

| Runtime | Path | Used by |
|---|---|---|
| Node 22.19.0 | `/opt/node22/bin` | xman (better-sqlite3 ABI), FableCut, photocraft static |
| system python3 | `/usr/bin/python3` | one-shot scripts |
| stevejobless venv | `/root/stevejobless/.venv/bin/python` | dash server (sqlalchemy) |

## External services (Cloudflare account `9546…713d`)

| Service | State |
|---|---|
| Zones: oddhobb.com, pogtown.com, pog.pet, pogtown? no — pogtown.com, humanvoiced.com, agentcom.org | active |
| Tunnel `figgsite` (54295d83) v6 | site origins :8797 (elsewhere) |
| Tunnel phone-agentcom (d458eedc) | agentcom.org→:8793, phone→:8794 |
| Email Routing → `cmail` worker | hello@ ×4 zones (+orders/support oddhobb) |
| Pages `humanvoiced` | humanvoiced.pages.dev + custom domain |
| R2 | media/assets; `CLOUDFLARE_R2_*` in vault |

## Secrets (vault `oracle` + dash vault — names only here)

`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `OPENCODE_API_KEY` (stale 401 —
use `~/.local/share/opencode/auth.json`), `X_*_ODDHOBB/POGTOWN`, `TELNYX_*`,
`ODDHOBB_PHONE_AUTH`, `GOOGLE_CLIENT_ID/SECRET_HV`, `YOUTUBE_API_KEY_*` (if sealed),
`R2_*`, `MESHY_*` (locked: ask before spend), `SERPAPI_API_KEY`.
No `FAL_KEY` yet — generative media deferred until sealed.

## Disk (7.1G free 2026-10-08 — watch it)

Big: xman `node_modules` 852M. Small: fablecut 18M, photocraft-web 24M,
fablecut-data (grows with footage — prune `exports/`).
Rules: no Rust source builds on this box, no Docker images (pruned),
`du -sh /root/*` before any new clone, keep ≥5G free.
