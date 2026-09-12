# coding-stats

Builds `src/data/coding-stats.json`, the anonymised weekly data behind
`/stats/` and the chart on the front page. Everything runs locally on the
machine that has the repos and the Claude Code transcripts (the MacBook);
only weekly totals end up in the JSON. No repo names, paths, session ids,
commit messages or chore notes are written to it.

## One-time setup

Clone this repo anywhere on the MacBook (it does not need to sit next to
your other repos), then write the config:

```sh
git clone git@github.com:AndyFooBlah/andrewbrook-dev.git
mkdir -p ~/.config/coding-stats
cat > ~/.config/coding-stats/config.json <<'JSON'
{
  "repos": ["~/dev/*"],
  "since": "2025-06-01",
  "authors": ["you@example.com", "12345+you@users.noreply.github.com"]
}
JSON
```

Config keys (all optional except `repos`; defaults in `collect.py`):

| key | meaning |
|---|---|
| `repos` | local checkouts to read; paths or globs (`~/dev/*` takes every git repo in that directory). Private repos are fine; they never appear in the output. |
| `since` | first date to count (ISO). |
| `authors` | author emails to count; empty = every author. |
| `exclude` | glob patterns of paths to ignore, added to the built-in list (lockfiles, images, `dist/**`, `vendor/**`, …). Use it for generated or vendored data that is not really code. |
| `ai_repos` | glob patterns of checkouts where every commit counts as AI-written, for repos only ever worked on through agents that left no attribution. |
| `exclude_repos` | glob patterns of checkouts to skip (e.g. `*/private-notes`). Second clones of the same remote are skipped automatically; the newest checkout wins. |
| `all_branches` | count every branch, not just `HEAD` (default false). |
| `ai_trailer_pattern` | regex matched against `Co-Authored-By` trailers and author emails; a match means AI-written. |
| `ai_body_pattern` | regex matched against the whole commit message (multiline) for agents that leave a body line instead of a trailer, e.g. `Assisted by Claude.` |
| `transcripts` | dirs to scan for Claude Code `*.jsonl` transcripts (default `~/.claude/projects`). |
| `idle_gap_minutes` | a gap between messages longer than this is not counted as active time. |
| `web_session_minutes` | estimated length of a claude.ai/code session (they leave no transcript). |
| `ledger`, `spend` | paths of the two JSONL ledgers below. |

## Refreshing the site

```sh
cd path/to/andrewbrook-dev
git pull
python3 scripts/coding-stats/collect.py   # writes src/data/coding-stats.json
git commit -am "Refresh coding stats" && git push
```

Python 3.9+ and `git`, nothing else. Takes a few seconds. `--out` defaults
to this checkout's data file, so the script can be run from any directory.

## Logging manual chores

Whenever an agent hands a task back to you (click something in a cloud
console, paste a secret, approve an OAuth screen…), log it:

```sh
path/to/andrewbrook-dev/scripts/coding-stats/chore.sh cloud-infra 15 "enabled the Vertex API"
```

Symlink it somewhere on your PATH so it is just `chore`:

```sh
ln -s "$PWD/scripts/coding-stats/chore.sh" ~/bin/chore
```

Categories: `cloud-infra`, `secrets-auth`, `accounts-billing`,
`dns-deploy`, `manual-testing`, `other`. The note is private.

To have Claude Code prompt you, add to `~/.claude/CLAUDE.md`:

> When you ask me to do something manually that you cannot do yourself
> (console clicks, secrets, account setup, DNS, testing on a device), end
> the message with a ready-to-run line
> `chore <category> <minutes> "<short note>"`
> using the closest category from cloud-infra, secrets-auth,
> accounts-billing, dns-deploy, manual-testing, other.

Ledger format (`~/.config/coding-stats/chores.jsonl`), one object per line:

```json
{"date": "2026-09-12", "category": "cloud-infra", "minutes": 15, "note": "enabled the Vertex API"}
```

## Logging spend

`~/.config/coding-stats/spend.jsonl`, one object per line:

```json
{"date": "2026-09-01", "amount": 200, "category": "claude", "note": "Max subscription"}
{"date": "2026-09-14", "amount": 50, "category": "claude", "note": "top-up"}
{"date": "2026-09-30", "period": "2026-09", "amount": 23.40, "category": "cloud", "note": "GCP invoice"}
{"date": "2026-09-30", "period": "2026-09", "amount": 12, "category": "other", "note": "domain renewal"}
```

Categories: `claude`, `cloud`, `other`. `period` (YYYY-MM) is the month the
charge covers; it defaults to the month of `date`. `claude` spend is spread
across the weeks of that month in proportion to Claude activity, so idle
weeks cost nothing; `cloud` and `other` are spread evenly by calendar day.
Precision is not the point; the page says so.

## How the split is decided

- **AI-written**: the commit has a `Co-Authored-By` trailer matching
  `ai_trailer_pattern` (Claude Code adds one on every commit it makes), or
  its author email matches the pattern (claude.ai/code commits are authored
  by `noreply@anthropic.com`; these count as yours even with `authors` set),
  or a line in its message matches `ai_body_pattern` (`Assisted by Claude.`
  on repos whose CLA bot rejects agent co-authors), or the checkout is
  listed in `ai_repos`. Everything else is **by hand**, including agent
  commits that carry no attribution at all, so "by hand" is generous. Squash merges must keep trailers or those commits
  count as hand-written.
- **Hours**: timestamps of user and assistant messages from every local
  transcript are merged (so parallel sessions are not double counted) and
  each gap contributes `min(gap, idle_gap_minutes)`.
- **Web sessions**: commits carrying a `Claude-Session:` trailer are from
  claude.ai/code; each distinct URL counts as one session of
  `web_session_minutes`. Older web commits without the trailer are counted as
  AI-written but not as sessions.
