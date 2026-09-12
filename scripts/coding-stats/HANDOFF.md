# Coding stats: handoff for a local Claude Code session

Context for whoever (human or agent) picks this up on the MacBook. The
feature is built and pushed on branch `claude/ai-coding-stats-dashboard-rslet2`;
what remains needs local files that the cloud session could not reach.

## What exists

- `/stats/` page (`src/pages/stats.astro`) and a front-page strip
  (`src/pages/index.astro`): headline figures, weekly charts, a table
  view, and methodology notes. Nav link added in `src/layouts/Base.astro`.
- Chart components: `src/components/WeeklyBars.astro` (stacked weekly
  columns, hover/focus tooltips), `CategoryBars.astro`, `StatTiles.astro`.
  Plain HTML/CSS, no chart library. Styles in `src/styles/global.css`
  under "stats viz"; Economist/FT-style (keyline, bold title, grey unit
  subtitle, horizontal hairline grid, dark baseline, source note, no boxes).
- Palette (validated for colour-vision deficiency and contrast on both
  surfaces): light `#006ba2 / #db444b / #3ebcd2`, dark
  `#1f80bb / #d9525a / #1fa3bb`, as `--series-1..3`.
- Data helpers in `src/lib/stats.ts`; data file `src/data/coding-stats.json`.
- Collector `scripts/coding-stats/collect.py` and chore logger `chore.sh`.
  Usage and ledger formats in `README.md` next to this file.

## Decisions already made (don't re-litigate)

- AI vs hand is decided per commit by the `Co-Authored-By: Claude` trailer.
  Hand edits before an agent commit are invisible; the page says so.
- Hours come from local Claude Code transcripts (`~/.claude/projects/**/*.jsonl`),
  merged across sessions, gaps capped at 15 min. Web sessions are counted
  from `Claude-Session:` trailers at an estimated 30 min each.
- Chores and spend are private JSONL ledgers under `~/.config/coding-stats/`.
  Chore categories: cloud-infra, secrets-auth, accounts-billing, dns-deploy,
  manual-testing, other. Spend categories: claude, cloud, other. Claude spend
  is spread by activity; cloud/other evenly across the billing month.
- The JSON contains weekly totals only. Never repo names, paths, session ids,
  commit messages, or chore notes. The repo list and ledgers stay on the Mac.
- Repos live in `/Users/wabbit/dev`. Author emails:
  `andrew.brook@fooblah.org`, `68444094+AndyFooBlah@users.noreply.github.com`.

## What's left (do on the MacBook)

1. Write `~/.config/coding-stats/config.json`:
   ```json
   {
     "repos": ["/Users/wabbit/dev/*"],
     "since": "2025-06-01",
     "authors": ["andrew.brook@fooblah.org", "68444094+AndyFooBlah@users.noreply.github.com"]
   }
   ```
   Drop the glob for an explicit list if `/Users/wabbit/dev` holds repos
   that shouldn't count. Check that `~/.claude/projects` exists and has
   `.jsonl` files; if Claude Code stores transcripts elsewhere on this
   machine, set `"transcripts"` in the config.
2. Seed `~/.config/coding-stats/spend.jsonl` with subscription months,
   top-ups, and GCP invoices (format in README.md). Ask Andy for amounts.
3. Backfill chores if worthwhile: grep the transcripts for phrases like
   "you'll need to", "in the console", "manually" and log what you find with
   `chore.sh`, with the right past date edited in. Timebox this.
4. Run `python3 scripts/coding-stats/collect.py`, read the stderr summary,
   then `npm ci && npm run dev` and check `/` and `/stats/` in both themes
   at desktop and phone width (no horizontal page scroll).
5. Commit `src/data/coding-stats.json` on this branch and push. Open a PR
   to `main` when Andy is happy with the numbers.
6. Optional: `ln -s "$PWD/scripts/coding-stats/chore.sh" ~/bin/chore` and
   add the CLAUDE.md snippet from README.md to `~/.claude/CLAUDE.md` so
   future sessions hand back a ready-made `chore …` line.

## Known gaps

- Web sessions before the `Claude-Session:` trailer existed are counted as
  AI-written commits but not as sessions or hours.
- Squash merges lose trailers; those commits count as hand-written.
- The committed data file is a baseline from this repo only until step 4.
