#!/bin/bash
# Log a manual chore: chore.sh <category> <minutes> [note]
# Categories: cloud-infra secrets-auth accounts-billing dns-deploy manual-testing other
# The note stays in the private ledger and is never published.
set -euo pipefail
LEDGER="${CODING_STATS_LEDGER:-$HOME/.config/coding-stats/chores.jsonl}"
cat="${1:?category}"; mins="${2:?minutes}"; note="${3:-}"
case "$cat" in
  cloud-infra|secrets-auth|accounts-billing|dns-deploy|manual-testing|other) ;;
  *) echo "unknown category: $cat" >&2; exit 1 ;;
esac
mkdir -p "$(dirname "$LEDGER")"
printf '{"date":"%s","category":"%s","minutes":%d,"note":%s}\n' \
  "$(date +%F)" "$cat" "$mins" "$(printf '%s' "$note" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')" \
  >> "$LEDGER"
echo "logged $cat ${mins}m -> $LEDGER"
