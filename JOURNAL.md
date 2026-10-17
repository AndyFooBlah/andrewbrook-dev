# Project journal

An append-only record of how andrewbrook.dev was built: **decisions** (and who made them), **friction**,
what we **learned**, what **surprised** us, and **incidents**.

**Format:** every entry starts with a UTC timestamp and a tag: `- 2026-10-16T17:52Z [decision] …`. Tags:
`[step]`, `[decision]`, `[friction]`, `[learning]`, `[surprise]`, `[incident]`, `[idea]`, `[milestone]`.
Entries before 2026-10-16T18:00Z were backfilled from commit times and session records, so their timestamps
are approximate (`~`). "Owner" is the site's owner; "session" is a Claude Code session.

**Append-only.** Never edit or delete a past entry. To correct one, append a new entry naming the earlier
one's timestamp. Synced daily to `andy-private-docs/journals/`.

---

- ~2026-07-29T20:00Z [decision] Owner wanted a simple blog and had registered andrewbrook.dev. Chose **Astro on GitHub Pages** over Substack/Ghost/Hugo: the content is Markdown with local SVG charts and code blocks, it lives next to the code it describes, it ships no client JavaScript by default, and there is nothing to migrate later. Substack would win on distribution if an email list ever matters more than control.
- ~2026-07-29T20:10Z [decision] **Posts live in the site repo, not in the project repos.** Project repos keep their technical docs for auditors; the blog keeps the narrative articles. One feed, one deploy, no cross-repo publishing. Recorded in `README.md` and `CLAUDE.md` so it survives between sessions.
- ~2026-07-29T20:15Z [decision] Charts are **generated artifacts owned by the producing repo** (e.g. `agent-time-bench/scripts/make_charts.py`), copied in by `scripts/sync-charts.sh`. `public/charts/**` is never hand-edited.
- ~2026-07-29T20:38Z [milestone] Site scaffolded and deployed: posts collection, writing/projects pages, RSS, light+dark (both explicitly specified, never an auto-flip), Pages deploy workflow (ab0ca65).
- ~2026-07-29T22:49Z [decision] Owner asked for the first post to stay unpublished for now. Drafts build in **dev only** — `getStaticPaths` filters on `import.meta.env.DEV` — so a draft is readable locally and genuinely absent from production rather than merely unlinked.
- ~2026-07-29T23:25Z [incident] `https://andrewbrook.dev` served a browser security warning. DNS was correct (all four A records, www CNAME); the certificate was `CN=*.github.io`. **Cause: with Actions-based Pages deploys the `CNAME` file in the build artifact does not register the custom domain** — unlike legacy branch deploys — so GitHub never requested a certificate for the domain. Setting the domain in the Pages config triggered issuance in ~60s; HTTPS enforcement re-enabled after. Documented in `README.md` and `CLAUDE.md` with the one-line `gh api` check.
- ~2026-07-29T23:20Z [learning] A verification of mine was wrong in a way worth remembering: `gcloud`/`gh`-style `--format="value(nested.list)"` renders an empty column for a populated nested list, which reads as "unset". Verify structured state with `--format=json`. The same mistake later produced a false "unrestricted API key" report on another project.
- ~2026-07-30T15:26Z [step] Projects page generated from `THEMES` + `REPOS` in `src/consts.ts`, grouped by theme, with posts auto-attaching to projects via each post's `repos:` frontmatter. Adding a project is a one-object edit.
- ~2026-08-02T01:43Z [friction] The owner edited the site through the GitHub web editor across five commits while the local clone sat four days stale. No conflict this time, but editing from two places needs a `git pull` habit before local work.
- ~2026-08-02T02:36Z [decision] Owner published the first post, retitled it, and added a **"Preface — a Note from Andy"** recording that the code is AI-written and lightly reviewed, with ~$200 of tokens spent and an explicit "review it before you deploy it". Their framing, in their voice, at the top — stronger than the tooling footnote it replaced.
- ~2026-08-29T15:52Z [step] Dropped the trailing tooling-disclosure paragraph; the owner's preface already covers it.
- ~2026-09-10T22:09Z [step] Deep-audit hygiene: `npm audit fix` (astro 7.1.6 → 7.3.2), Apache-2.0 + CC BY 4.0 licences, Dependabot enabled (npm weekly grouped, actions monthly).
- ~2026-09-12T00:10Z [milestone] Second and third posts: Grammar Garden, and the Wind Spirit balancer.
- ~2026-09-12T15:07Z [milestone] Coding stats page and front-page chart shipped, with a collector runnable from any directory and a daily launchd refresh.
- ~2026-09-12T12:42Z [decision] Spend figures pulled off the stats and front pages until billing collection is trustworthy — better absent than wrong.
- ~2026-09-12T21:39Z [learning] The stats page carries a stated blind spot (Gemini CLI / Antigravity) rather than implying full coverage; later addressed by reading those logs directly (2026-09-18).
- ~2026-09-12T22:01Z [step] Removed the "honest" lead-in tic from three posts at the owner's request; the word is reserved for genuine contrast with deceit.
- ~2026-09-18T16:15Z [step] Stats freshness check added, plus Jev (TypeSafe) spend collected from the proxy's request log. Four Dependabot Actions majors merged after the audit verified them.
- 2026-10-16T18:05Z [step] Journal created and backfilled from commit history and session records, per the owner's new global journal policy in `~/.claude/CLAUDE.md`.

- 2026-10-17T04:52Z [incident] **Backfilled timestamps in this journal are seven hours early and are not UTC.**
  Spot-checked against the commits they cite: entries generated with
  `git log --date=format:'%Y-%m-%dT%H:%MZ'` render each commit in its own local zone (here PDT,
  UTC-7) and then have a literal `Z` appended by the format string, so the `Z` is wrong. Add seven
  hours to any entry that was derived from commit times. Entries written from session chronology
  rather than from that command are unaffected, so this journal may mix both.
- 2026-10-17T04:52Z [learning] Correct incantation for a UTC backfill:
  `TZ=UTC git log --date=format-local:'%Y-%m-%dT%H:%MZ'` — `format-local`, not `format`. Appending a
  literal `Z` to a local-time format produces timestamps that look authoritative and are silently
  wrong, which is worse than an obviously missing timezone. This hit several repos in the
  2026-10-16 journal rollout, independently, because the same command was used in each.
- 2026-10-17T04:52Z [decision] Corrected by appending rather than editing the entries above, per the append-only
  rule.
