#!/bin/bash
# Copy generated charts from sibling project repos into public/charts/<repo>/.
#
# Charts are GENERATED artifacts owned by the project that produces them (e.g.
# agent-time-bench/scripts/make_charts.py). This script is the one-way seam:
# regenerate charts there, sync here, commit. Never hand-edit public/charts.
set -euo pipefail
cd "$(dirname "$0")/.."

sync_repo() { # repo-dir-name  source-subdir
  local repo="$1" src="$2"
  local from="../$repo/$src"
  if [ ! -d "$from" ]; then
    echo "skip $repo (no $src — is the repo checked out alongside this one?)"
    return
  fi
  mkdir -p "public/charts/$repo"
  rsync -a --delete --include='*/' --include='*.svg' --include='*.png' --exclude='*' \
    "$from/" "public/charts/$repo/"
  echo "synced $repo: $(find "public/charts/$repo" -type f | wc -l | tr -d ' ') files"
}

sync_repo agent-time-bench blog/charts

echo "done — reference charts in posts as /charts/<repo>/<file>.svg"
