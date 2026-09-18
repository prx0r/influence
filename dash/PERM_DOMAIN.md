# Permanent domain: influence.intelligentothers.xyz

Public dash for the influence backend. Token gate enforced. No secrets in
this file or in the repo. Tokens live in `dash/.token` (0600) and tunnel
credentials in `~/.cloudflared/influence-dash-creds.json` (0600).

## What

- Hostname: `influence.intelligentothers.xyz` (CNAME -> tunnel, proxied)
- Zone: `intelligentothers.xyz`
- Named tunnel: `influence-dash`
- Tunnel ID: `9be36151-4294-4859-b98d-7933edef7f0f`
- Ingress: hostname -> `http://127.0.0.1:8793`, catch-all 404
- Dash binds loopback only. Public arrives only through the tunnel.
- `/api/health` is public. Everything else needs `?token=` from `dash/.token`.

## Operate

```bash
./dash/serve-perm.sh          # ensure dash + tunnel up, print URLs + status
./dash/serve-perm.sh status   # health local + public, tunnel conns, no token values

# Manual restart (if needed):
# dash: DASH_TOKEN=$(cat dash/.token) DASH_PORT=8793 LIVE=1 \
#   DASH_DB=$PWD/dash/influence.db PATH="$PWD/.venv/bin:$PATH" \
#   nohup python3 dash/server.py > dash/dash.log 2>&1 & echo $! > dash/.dash.pid
# tunnel: nohup cloudflared tunnel \
#   --config ~/.cloudflared/influence-dash.yml run influence-dash \
#   > dash/tunnel-perm.log 2>&1 & echo $! > dash/.tunnel-perm.pid
```

## Verify (no token values printed)

```bash
curl -s https://influence.intelligentothers.xyz/api/health
# -> {"ok": true, "dash": "influence"}
curl -s -o /dev/null -w "%{http_code}\n" \
  https://influence.intelligentothers.xyz/api/state
# -> 403 (gate holds)
DASH_TOKEN=$(cat dash/.token); curl -s \
  "https://influence.intelligentothers.xyz/api/state?token=$DASH_TOKEN" \
  | head -c 200
```

## Cloudflare API via vault (no keys in shell)

The `cloudflare` vault holds `CF_API_TOKEN`. A `cloudflare-api` service
maps `api.cloudflare.com` to bearer auth, so calls go through the proxy
without printing keys:

```bash
agent-vault vault run --vault cloudflare -- \
  curl -s "https://api.cloudflare.com/client/v4/zones?per_page=50"
```

## Retired

Quick tunnel (`*.trycloudflare.com`) is superseded. `dash/tunnel.log` and
`.tunnel.pid` are the old quick-tunnel artifacts. Permanent path uses
`tunnel-perm.log` + `.tunnel-perm.pid`.
