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
scripts/coding-stats/launchd/install.sh --now   # --now also runs it immediately
tail -f ~/Library/Logs/coding-stats.log
```

The committed plist writes its log to `__HOME__/Library/Logs/coding-stats.log`;
launchd does not expand `$HOME` in a plist, so `install.sh` substitutes your
home directory while copying it into `~/Library/LaunchAgents/`. Do not copy the
plist by hand. Re-running the installer replaces the loaded job.

Remove with `launchctl bootout gui/$(id -u)/dev.andrewbrook.coding-stats`.
The job needs the same one-time setup as a manual run: the config in
`~/.config/coding-stats/`, `gcloud auth application-default login`, and git
push access (the macOS keychain credential helper works under launchd).
