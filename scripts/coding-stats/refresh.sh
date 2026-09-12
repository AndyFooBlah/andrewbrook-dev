#!/bin/bash
# Refresh src/data/coding-stats.json from this Mac and push it to main.
# Meant to run unattended (launchd, see launchd/README.md); uses its own
# disposable clone so it never touches a working checkout.
set -euo pipefail
export PATH="/opt/homebrew/bin:/opt/homebrew/share/google-cloud-sdk/bin:/usr/local/bin:/usr/bin:/bin"
REPO="${CODING_STATS_CLONE:-$HOME/.local/share/coding-stats/andrewbrook-dev}"
URL="https://github.com/AndyFooBlah/andrewbrook-dev.git"
log() { printf '%s %s\n' "$(date '+%F %T')" "$*"; }

if [ ! -d "$REPO/.git" ]; then
  mkdir -p "$(dirname "$REPO")"
  git clone -q "$URL" "$REPO"
  log "cloned into $REPO"
fi
cd "$REPO"
git fetch -q origin main
git checkout -q -B main origin/main      # this clone is disposable: always match origin

python3 scripts/coding-stats/detect_chores.py
python3 scripts/coding-stats/collect.py

if git diff --quiet -- src/data/coding-stats.json; then
  log "no change"
  exit 0
fi
git add src/data/coding-stats.json
# A bot identity, so the collector's author filter ignores these commits.
git -c user.name="coding-stats" -c user.email="coding-stats@andrewbrook.dev" \
  commit -q -m "Refresh coding stats" -- src/data/coding-stats.json
git push -q origin main || { git pull -q --rebase origin main && git push -q origin main; }
log "pushed $(git rev-parse --short HEAD)"
