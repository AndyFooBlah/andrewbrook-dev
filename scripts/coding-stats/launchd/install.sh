#!/bin/bash
# Install (or reinstall) the daily coding-stats launchd job for the current user.
#
# launchd does not expand $HOME or ~ inside a plist, and StandardOutPath /
# StandardErrorPath must be absolute, so the committed plist carries a
# __HOME__ placeholder and this script substitutes the real home directory
# on the way into ~/Library/LaunchAgents. Pass --now to also run it once.
set -euo pipefail

LABEL="dev.andrewbrook.coding-stats"
SRC="$(cd "$(dirname "$0")" && pwd)/$LABEL.plist"
DEST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
sed "s|__HOME__|$HOME|g" "$SRC" > "$DEST"
plutil -lint "$DEST" >/dev/null

# Replace any previously loaded copy; bootout fails harmlessly when none is loaded.
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$DEST"
echo "installed $DEST (log: $HOME/Library/Logs/coding-stats.log)"

if [ "${1:-}" = "--now" ]; then
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
  echo "started $LABEL"
fi
