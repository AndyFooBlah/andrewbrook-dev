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
| `unattributed_ai_until` | ISO date. Commits before it with no attribution still count as AI-written (for history from before you started leaving trailers on every hand commit); from that date on they count as by hand. |
| `exclude_repos` | glob patterns of checkouts to skip (e.g. `*/private-notes`). Second clones of the same remote are skipped automatically; the newest checkout wins. |
| `all_branches` | count every branch, not just `HEAD` (default false). |
| `ai_trailer_pattern` | regex matched against `Co-Authored-By` trailers and author emails; a match means AI-written. |
| `ai_body_pattern` | regex matched against the whole commit message (multiline) for agents that leave a body line instead of a trailer, e.g. `Assisted by Claude.` |
| `transcripts` | dirs to scan for Claude Code `*.jsonl` transcripts (default `~/.claude/projects`). |
| `idle_gap_minutes` | a gap between messages longer than this is not counted as active time. |
| `web_session_minutes` | estimated length of a claude.ai/code session (they leave no transcript). |
| `ledger`, `spend` | paths of the two JSONL ledgers below. |
| `auto_ledger` | chores found in transcripts by `detect_chores.py` (default `~/.config/coding-stats/chores-auto.jsonl`). |
| `chore_detector` | `{"project": "...", "location": "global", "model": "gemini-3.5-flash-lite"}`: the Vertex AI project and model `detect_chores.py` classifies with. |
| `subscriptions` | flat-rate plans, charged automatically each billing cycle: `[{"category": "claude", "amount": 200, "since": "2026-01-26", "until": null, "note": "Claude Max 20x"}]`. Charges land on the day-of-month of `since`. |
| `jev_proxy_logs` | `{"project": "...", "service": "..."}`: the Cloud Run service whose request log carries `jsonPayload.provider="typesafe"` and `costUsd`; daily Jev (TypeSafe) cost is read from it and persisted in `spend_auto`, since logs expire after 30 days. |
| `spend_auto` | ledger the collectors above write (default `~/.config/coding-stats/spend-auto.jsonl`); never edit by hand. |
| `gcp_billing_export` | `{"project": "...", "dataset": "..."}` of a BigQuery dataset holding Cloud Billing `gcp_billing_export_v1_*` tables; net daily cost (credits applied) is booked as `cloud` spend. Needs the `bq` CLI and an account that can query the dataset. |

## Refreshing the site

A launchd job does this daily on the MacBook; see `launchd/README.md`.
By hand it is:

```sh
cd path/to/andrewbrook-dev
git pull
python3 scripts/coding-stats/detect_chores.py   # new chores from transcripts
python3 scripts/coding-stats/collect.py         # writes src/data/coding-stats.json
git commit -am "Refresh coding stats" && git push
```

Python 3.9+, `git`, and the gcloud SDK (`bq` for billing, ADC for the chore
detector). Takes under a minute. `--out` defaults to this checkout's data
file, so the collector can be run from any directory.

## Chores

Most chores are found automatically. `detect_chores.py` takes the last
assistant message of every turn in the local transcripts and asks a small
Gemini model on Vertex AI (in your own project; run
`gcloud auth application-default login` once and enable the Vertex AI API)
whether the agent handed a task back to you: run this in your terminal,
click through a console, paste a secret, test it on your phone. Each hit is
appended to the auto ledger with an estimated duration and the message uuid,
so nothing is classified twice. Run it before the collector:

```sh
python3 scripts/coding-stats/detect_chores.py     # --dry-run to preview, --limit N to sample
python3 scripts/coding-stats/collect.py
```

Sessions run on claude.ai/code or the phone leave no local transcript, so
their chores are missed. For those, or anything else, log by hand: whenever
an agent hands a task back to you (click something in a cloud console, paste
a secret, approve an OAuth screen…), run:

```sh
path/to/andrewbrook-dev/scripts/coding-stats/chore.sh cloud-infra 15 "enabled the Vertex API"
```

Symlink it somewhere on your PATH so it is just `chore`:

```sh
ln -s "$PWD/scripts/coding-stats/chore.sh" ~/bin/chore
```

Categories: `terminal`, `cloud-infra`, `secrets-auth`, `accounts-billing`,
`dns-deploy`, `manual-testing`, `other`. The note is private.

To have Claude Code prompt you, add to `~/.claude/CLAUDE.md`:

> When you ask me to do something manually that you cannot do yourself
> (console clicks, secrets, account setup, DNS, testing on a device), end
> the message with a ready-to-run line
> `chore <category> <minutes> "<short note>"`
> using the closest category from terminal, cloud-infra, secrets-auth,
> accounts-billing, dns-deploy, manual-testing, other.

Ledger format (`~/.config/coding-stats/chores.jsonl`), one object per line:

```json
{"date": "2026-09-12", "category": "cloud-infra", "minutes": 15, "note": "enabled the Vertex API"}
```

## Spend

Most spend is collected automatically:

- **Claude subscription**: list it under `subscriptions` in the config; the
  collector books one charge per billing cycle. Usage credits bought on top
  of the plan are not visible to any API, so log those by hand (below).
- **Jev (TypeSafe)**: every call goes through wind-spirit's llm-proxy on Cloud
  Run, which logs the request with its cost at TypeSafe's list price. Point
  `jev_proxy_logs` at it; days are persisted locally because the log expires.
- **Google Cloud**: enable Cloud Billing export to BigQuery once per billing
  account (console only: Billing → Billing export → BigQuery export →
  *Standard usage cost* → pick the project/dataset) and point
  `gcp_billing_export` at the dataset. Data starts flowing from the day it
  is enabled, plus the current and previous month when the dataset is in a
  multi-region location; older invoices are not backfilled.

Anything else goes in `~/.config/coding-stats/spend.jsonl`, one object per line:

```json
{"date": "2026-09-01", "amount": 200, "category": "claude", "note": "Max subscription"}
{"date": "2026-09-14", "amount": 50, "category": "claude", "note": "top-up"}
{"date": "2026-09-30", "period": "2026-09", "amount": 23.40, "category": "cloud", "note": "GCP invoice"}
{"date": "2026-09-30", "period": "2026-09", "amount": 12, "category": "other", "note": "domain renewal"}
```

Categories: `claude`, `jev`, `cloud`, `other`. `period` (YYYY-MM) is the month the
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
  on repos whose CLA bot rejects agent co-authors), the checkout is listed
  in `ai_repos`, or the commit predates `unattributed_ai_until`. Everything
  else is **by hand**, including agent commits that carry no attribution at
  all, so "by hand" is generous. Squash merges must keep trailers or those commits
  count as hand-written.
- **Hours**: timestamps of user and assistant messages from every local
  transcript are merged (so parallel sessions are not double counted) and
  each gap contributes `min(gap, idle_gap_minutes)`.
- **Web sessions**: commits carrying a `Claude-Session:` trailer are from
  claude.ai/code; each distinct URL counts as one session of
  `web_session_minutes`. Older web commits without the trailer are counted as
  AI-written but not as sessions.
