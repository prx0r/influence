#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
DEST="$ROOT/upstreams"
mkdir -p "$DEST"
repos=(
  "https://github.com/tddworks/asc-cli.git"
  "https://github.com/blitzdotdev/blitz-mac.git"
  "https://github.com/browserbase/stagehand.git"
  "https://github.com/activepieces/activepieces.git"
  "https://github.com/gitroomhq/postiz-app.git"
)
for repo in "${repos[@]}"; do
  name="$(basename "$repo" .git)"
  if [[ -d "$DEST/$name/.git" ]]; then
    echo "[skip] $name already cloned"
  else
    echo "[clone] $name"
    git clone --depth 1 "$repo" "$DEST/$name"
  fi
  (cd "$DEST/$name" && printf '%-24s %s\n' "$name" "$(git rev-parse HEAD)")
done | tee "$DEST/PINNED_SHAS.txt"
