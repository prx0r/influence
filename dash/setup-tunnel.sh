#!/bin/bash
# Setup agentcom.org tunnel — run this once
set -e

echo "=== Step 1: Login to Cloudflare (opens browser) ==="
cloudflared tunnel login
echo ""

echo "=== Step 2: Create tunnel ==="
cloudflared tunnel create agentcom
TUNNEL_ID=$(cloudflared tunnel list | grep agentcom | awk '{print $1}')
echo "Tunnel ID: $TUNNEL_ID"

echo ""
echo "=== Step 3: Route DNS ==="
cloudflared tunnel route dns agentcom agentcom.org

echo ""
echo "=== Step 4: Create config ==="
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/agentcom.yml << EOF
tunnel: $TUNNEL_ID
credentials-file: ~/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: agentcom.org
    service: http://localhost:8793
  - service: http_status:404
EOF
echo "Config written to ~/.cloudflared/agentcom.yml"

echo ""
echo "=== Step 5: Run tunnel ==="
echo "cloudflared tunnel run agentcom"
echo ""
echo "Or use the dash launcher:"
echo "cd /home/box/influence && python3 dash/launch.py --slug pow-systems --port 8793"
echo ""
echo "Dashboard: http://127.0.0.1:8793"
echo "Public: https://agentcom.org"
