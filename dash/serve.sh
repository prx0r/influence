#!/bin/bash
# Serve influence dash on loopback. Token persisted in dash/.token (0600, gitignored).
# With --tunnel, also opens a Cloudflare quick tunnel (requires DASH_TOKEN, always set here).
set -e
cd "$(dirname "$0")"
TOKFILE=.token
if [ ! -f "$TOKFILE" ]; then
  python3 -c "import secrets; print(secrets.token_urlsafe(24))" > "$TOKFILE"
  chmod 600 "$TOKFILE"
fi
export DASH_TOKEN="$(cat "$TOKFILE")"
export DASH_PORT="${DASH_PORT:-8793}"
export LIVE="${LIVE:-0}"
export DASH_DB="${DASH_DB:-$PWD/influence.db}"
export DASH_JOURNAL="${DASH_JOURNAL:-$PWD/decisions.db}"
export PATH="/home/ubuntu/influence/.venv/bin:$PATH"
echo "dash token: $DASH_TOKEN"
echo "open: http://127.0.0.1:$DASH_PORT/?token=$DASH_TOKEN"
if [ "$1" == "--tunnel" ]; then
  nohup python3 server.py > dash.log 2>&1 &
  echo $! > .dash.pid
  nohup cloudflared tunnel --url "http://127.0.0.1:$DASH_PORT" --no-autoupdate > tunnel.log 2>&1 &
  echo $! > .tunnel.pid
  sleep 6
  grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" tunnel.log | head -n 1 || tail -n 5 tunnel.log
else
  exec python3 server.py
fi
