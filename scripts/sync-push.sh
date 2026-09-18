#!/bin/bash
# One-command sync + scan + commit + push. Kills the copy-divergence risk:
# /tmp/cmail-repo is DERIVED from /root trees, never edited directly.
# Usage: ./scripts/sync-push.sh "commit message"
set -euo pipefail
MSG="${1:?usage: ./scripts/sync-push.sh \"commit message\"}"
REPO=/tmp/cmail-repo

echo "== sync from /root"
rm -rf "$REPO/cmail" "$REPO/stevejobless" "$REPO/domainnamechecker"
cp -r /root/cmail "$REPO/cmail"
cp -r /root/stevejobless "$REPO/stevejobless"
cp -r /root/domainnamechecker "$REPO/domainnamechecker"
rm -rf "$REPO/cmail/node_modules" "$REPO/cmail/.wrangler" \
  "$REPO/stevejobless/.venv" "$REPO/stevejobless/.git" "$REPO/stevejobless/stevejobless.db" \
  "$REPO/domainnamechecker/.git" "$REPO/domainnamechecker/worker/node_modules" \
  "$REPO/domainnamechecker/worker-v4/node_modules"
find "$REPO" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$REPO" -name "*.db*" | grep -v ".git/" | head -3 && { echo "DB LEAK"; exit 1; } || true

echo "== secret scan"
if grep -rIlE "cfat_[A-Za-z0-9_-]{10,}|ghp_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{10,}|AIza[0-9A-Za-z_-]{10,}" \
  "$REPO" --exclude-dir=node_modules --exclude-dir=.git 2>/dev/null | head -5; then
  echo "SCAN RESULT ABOVE — aborting, remove secrets first"; exit 1
fi
echo "scan clean"

echo "== suites (fail closed)"
(cd /root/stevejobless && .venv/bin/python -m pytest tests/ -q 2>&1 | tail -1)
(cd /root/cmail && npx tsc --noEmit && npx vitest run 2>&1 | grep -E "Tests ")

echo "== commit + push (needs GH_TOKEN env)"
cd "$REPO" && git add -A
git -c user.name="prx0r" -c user.email="tradesprior@gmail.com" commit -qm "$MSG"
printf '#!/bin/sh\nexec echo "$GH_TOKEN"\n' > /tmp/.askpass-cmail.sh && chmod 700 /tmp/.askpass-cmail.sh
export GH_TOKEN="${GH_TOKEN:?set GH_TOKEN first}"
GIT_ASKPASS=/tmp/.askpass-cmail.sh git -c credential.helper= push https://prx0r@github.com/prx0r/cmail.git main 2>&1 | tail -2
shred -u /tmp/.askpass-cmail.sh; unset GH_TOKEN
echo "pushed."
