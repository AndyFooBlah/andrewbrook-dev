# Daily refresh (launchd)

`dev.andrewbrook.coding-stats.plist` runs `refresh.sh` every day at 21:30
local time. If the Mac is asleep at that moment, launchd runs it at the next
wake, so a missed day catches up on its own. The job keeps its own clone in
`~/.local/share/coding-stats/andrewbrook-dev`, runs the chore detector and
the collector, and pushes a "Refresh coding stats" commit to `main` (as a
bot identity the collector ignores) whenever the data changed. GitHub
Actions then deploys the site.

Install (once, on the MacBook):

```sh
cp scripts/coding-stats/launchd/dev.andrewbrook.coding-stats.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/dev.andrewbrook.coding-stats.plist
launchctl kickstart -k gui/$(id -u)/dev.andrewbrook.coding-stats   # run it now
tail -f ~/Library/Logs/coding-stats.log
```

Remove with `launchctl bootout gui/$(id -u)/dev.andrewbrook.coding-stats`.
The job needs the same one-time setup as a manual run: the config in
`~/.config/coding-stats/`, `gcloud auth application-default login`, and git
push access (the macOS keychain credential helper works under launchd).
