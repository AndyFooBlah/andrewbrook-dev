#!/usr/bin/env python3
"""Aggregate AI-vs-hand coding stats into one anonymised weekly JSON file.

Sources (all read locally, nothing leaves the machine except the output):

  git repos      lines/commits per week, split AI vs hand by the
                 "Co-Authored-By: Claude" trailer that Claude Code writes.
  transcripts    ~/.claude/projects/**/*.jsonl -> active minutes with Claude.
  chores.jsonl   manual tasks you logged (scripts/coding-stats/chore.sh).
  spend.jsonl    subscription, top-ups, cloud bills -> dollars per week.

The output contains ONLY weekly totals. No repo names, paths, session ids,
commit messages or chore notes are ever written to it.

Usage:
  collect.py [--config ~/.config/coding-stats/config.json] [--out FILE]

--out defaults to src/data/coding-stats.json in this checkout, so it works
from any working directory.

See README.md next to this script for the config and ledger formats.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys
from collections import defaultdict

CHORE_CATEGORIES = [
    "cloud-infra",      # console/CLI changes in GCP, AWS, etc.
    "secrets-auth",     # keys, OAuth consent screens, tokens, 2FA
    "accounts-billing", # sign-ups, billing, quotas, plan changes
    "dns-deploy",       # DNS, Pages settings, app-store style releases
    "manual-testing",   # clicking through the thing to see if it works
    "other",
]
SPEND_CATEGORIES = ["claude", "cloud", "other"]

DEFAULTS = {
    "since": "2025-01-01",
    "exclude": [
        "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock",
        "poetry.lock", "uv.lock", "go.sum", "*.svg", "*.png", "*.jpg",
        "*.min.js", "*.min.css", "dist/**", "build/**", "node_modules/**",
        "public/charts/**", "vendor/**", "third_party/**", "*.pbxproj",
        "gradlew", "gradlew.bat",
    ],
    "exclude_repos": [],           # glob patterns of checkouts to skip
    "ai_repos": [],                # checkouts where every commit is AI-written
    "unattributed_ai_until": None, # ISO date; unattributed commits before it are AI
    "authors": [],                 # author emails to count; [] = everyone
    "all_branches": False,
    "ai_trailer_pattern": r"claude|anthropic",
    # Matched (multiline, case-insensitive) against the whole commit message
    # for agents that leave a body line instead of a trailer.
    "ai_body_pattern": r"^\s*(assisted by|generated with|🤖 generated with)\b.*\b(claude|gemini|codex|copilot)\b",
    "transcripts": ["~/.claude/projects"],
    "idle_gap_minutes": 15,
    "web_session_minutes": 30,     # estimate per remote (claude.ai/code) session
    "ledger": "~/.config/coding-stats/chores.jsonl",
    "spend": "~/.config/coding-stats/spend.jsonl",
}


# --------------------------------------------------------------- helpers

def expand(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def week_key(d: dt.date) -> str:
    """Monday of the ISO week, as YYYY-MM-DD."""
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def parse_ts(s: str) -> dt.datetime:
    # git %aI and transcript timestamps are both ISO 8601.
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def excluded(path: str, patterns: list[str]) -> bool:
    base = os.path.basename(path)
    for pat in patterns:
        if pat.endswith("/**"):
            if path.startswith(pat[:-3] + "/") or ("/" + pat[:-3] + "/") in path:
                return True
        elif fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(base, pat):
            return True
    return False


def new_week() -> dict:
    return {
        "ai_added": 0, "ai_deleted": 0, "hand_added": 0, "hand_deleted": 0,
        "ai_commits": 0, "hand_commits": 0,
        "claude_minutes": 0.0, "sessions": 0, "web_sessions": 0,
        "chores": {c: 0 for c in CHORE_CATEGORIES},
        "chore_minutes": 0,
        "spend": {c: 0.0 for c in SPEND_CATEGORIES},
    }


# ------------------------------------------------------------------- git

def git_out(repo: str, *args: str) -> str | None:
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def remote_key(repo: str) -> str:
    """Identify a checkout by its origin remote so duplicate clones count once."""
    url = git_out(repo, "remote", "get-url", "origin") or ""
    m = re.search(r"([^/:]+/[^/]+?)(?:\.git)?/?$", url)
    return m.group(1).lower() if m else repo


def repo_dirs(patterns: list[str], skip: list[str] = ()) -> list[str]:
    """Expand config 'repos' entries (paths or globs like ~/dev/*) to git repos.

    Checkouts matching a `skip` glob or with no commits are skipped, and two checkouts of the same
    remote count once (the one whose HEAD is newest wins), so a stray second
    clone does not double count.
    """
    found: dict[str, tuple[int, str]] = {}   # remote key -> (head time, path)
    order: list[str] = []
    for pat in patterns:
        matches = sorted(glob.glob(expand(pat))) or [expand(pat)]
        for path in matches:
            if any(fnmatch.fnmatch(path, expand(x)) for x in skip):
                continue
            if not os.path.isdir(os.path.join(path, ".git")):
                if not any(ch in pat for ch in "*?["):
                    print(f"skip (not a git repo): {path}", file=sys.stderr)
                continue
            head = git_out(path, "log", "-1", "--format=%ct")
            if not head:
                print(f"skip (no commits): {path}", file=sys.stderr)
                continue
            key = remote_key(path)
            if key in found:
                if found[key][1] == path:
                    continue
                if int(head) > found[key][0]:
                    print(f"skip (same remote as {path}): {found[key][1]}", file=sys.stderr)
                    found[key] = (int(head), path)
                else:
                    print(f"skip (same remote as {found[key][1]}): {path}", file=sys.stderr)
                continue
            found[key] = (int(head), path)
            order.append(key)
    return [found[k][1] for k in order]


def collect_git(cfg: dict, weeks: dict) -> tuple[int, set[str]]:
    """Fill lines/commits per week. Returns (repo count, web session urls)."""
    ai_re = re.compile(cfg["ai_trailer_pattern"], re.I)
    body_re = re.compile(cfg["ai_body_pattern"], re.I | re.M)
    authors = {a.lower() for a in cfg["authors"]}
    web_sessions: set[str] = set()
    cutoff = cfg["unattributed_ai_until"]
    ai_until = dt.date.fromisoformat(cutoff) if cutoff else None
    fmt = ("%x1e%H%x1f%aI%x1f%ae%x1f"
           "%(trailers:key=Co-Authored-By,valueonly,separator=|)%x1f"
           "%(trailers:key=Claude-Session,valueonly,separator=|)%x1f%B%x1f")
    n = 0
    for repo in repo_dirs(cfg["repos"], cfg["exclude_repos"]):
        n += 1
        # Repos worked on only through agents that left no attribution.
        repo_ai = any(fnmatch.fnmatch(repo, expand(x)) for x in cfg["ai_repos"])
        cmd = ["git", "-C", repo, "log", "--no-merges", "--numstat",
               f"--since={cfg['since']}", f"--format={fmt}"]
        if cfg["all_branches"]:
            cmd.append("--all")
        out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
        for rec in out.split("\x1e"):
            if not rec.strip():
                continue
            header, _, body = rec.rpartition("\x1f")
            sha, date, email, coauth, session, message = header.split("\x1f")
            # Commits the agent authored itself (claude.ai/code commits carry
            # author noreply@anthropic.com) are yours even with `authors` set.
            ai_author = bool(ai_re.search(email))
            if authors and email.lower() not in authors and not ai_author:
                continue
            day = parse_ts(date).date()
            is_ai = (repo_ai or ai_author or bool(ai_re.search(coauth))
                     or bool(body_re.search(message))
                     or (ai_until is not None and day < ai_until))
            wk = weeks[week_key(day)]
            added = deleted = 0
            for line in body.splitlines():
                parts = line.split("\t")
                if len(parts) != 3 or parts[0] == "-":
                    continue
                if excluded(parts[2], cfg["exclude"]):
                    continue
                added += int(parts[0])
                deleted += int(parts[1])
            if is_ai:
                wk["ai_added"] += added
                wk["ai_deleted"] += deleted
                wk["ai_commits"] += 1
            else:
                wk["hand_added"] += added
                wk["hand_deleted"] += deleted
                wk["hand_commits"] += 1
            for url in filter(None, session.split("|")):
                url = url.strip()
                if url not in web_sessions:
                    web_sessions.add(url)
                    wk["web_sessions"] += 1
    return n, web_sessions


# ----------------------------------------------------------- transcripts

def collect_transcripts(cfg: dict, weeks: dict) -> int:
    """Sum active minutes across all local Claude Code sessions.

    Every user/assistant message timestamp is an "activity" point. Activity
    points from all sessions are merged so parallel sessions are not double
    counted, then each gap between consecutive points contributes
    min(gap, idle_gap). Returns number of transcript files read.
    """
    since = parse_ts(cfg["since"] + "T00:00:00+00:00")
    gap_cap = cfg["idle_gap_minutes"] * 60.0
    points: list[dt.datetime] = []
    session_start: dict[str, dt.datetime] = {}
    files = 0
    for root in cfg["transcripts"]:
        for path in glob.glob(os.path.join(expand(root), "**", "*.jsonl"), recursive=True):
            files += 1
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") not in ("user", "assistant") or "timestamp" not in o:
                        continue
                    try:
                        ts = parse_ts(o["timestamp"])
                    except ValueError:
                        continue
                    if ts < since:
                        continue
                    points.append(ts)
                    sid = o.get("sessionId") or path
                    if sid not in session_start or ts < session_start[sid]:
                        session_start[sid] = ts
    points.sort()
    for a, b in zip(points, points[1:]):
        gap = (b - a).total_seconds()
        weeks[week_key(a.date())]["claude_minutes"] += min(gap, gap_cap) / 60.0
    for ts in session_start.values():
        weeks[week_key(ts.date())]["sessions"] += 1
    return files


# ---------------------------------------------------------------- ledgers

def read_jsonl(path: str) -> list[dict]:
    path = expand(path)
    if not os.path.exists(path):
        print(f"note: no file at {path}", file=sys.stderr)
        return []
    rows = []
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                sys.exit(f"{path}:{i}: bad JSON ({e})")
    return rows


def collect_chores(cfg: dict, weeks: dict) -> int:
    rows = read_jsonl(cfg["ledger"])
    for r in rows:
        cat = r.get("category", "other")
        if cat not in CHORE_CATEGORIES:
            sys.exit(f"chores: unknown category {cat!r}; use one of {CHORE_CATEGORIES}")
        wk = weeks[week_key(dt.date.fromisoformat(r["date"]))]
        wk["chores"][cat] += 1
        wk["chore_minutes"] += int(r.get("minutes", 0))
    return len(rows)


def month_weeks(period: str) -> list[tuple[str, int]]:
    """(week_key, days-of-that-week-inside-month) for a YYYY-MM period."""
    y, m = (int(x) for x in period.split("-"))
    first = dt.date(y, m, 1)
    nxt = dt.date(y + (m == 12), (m % 12) + 1, 1)
    counts: dict[str, int] = defaultdict(int)
    d = first
    while d < nxt:
        counts[week_key(d)] += 1
        d += dt.timedelta(days=1)
    return list(counts.items())


def collect_spend(cfg: dict, weeks: dict) -> int:
    """Spread each spend row across the weeks of its period.

    "claude" spend is spread in proportion to Claude activity (transcript
    minutes plus the web-session estimate) so idle weeks cost nothing;
    everything else (cloud bills etc.) is spread evenly by calendar day.
    """
    rows = read_jsonl(cfg["spend"])
    est = cfg["web_session_minutes"]
    for r in rows:
        cat = r.get("category", "other")
        if cat not in SPEND_CATEGORIES:
            sys.exit(f"spend: unknown category {cat!r}; use one of {SPEND_CATEGORIES}")
        amount = float(r["amount"])
        period = r.get("period") or r["date"][:7]
        mw = month_weeks(period)
        if cat == "claude":
            act = {wk: weeks[wk]["claude_minutes"] + est * weeks[wk]["web_sessions"]
                   for wk, _ in mw}
            total = sum(act.values())
            if total > 0:
                for wk, a in act.items():
                    weeks[wk]["spend"][cat] += amount * a / total
                continue  # fall through to even spread when there was no activity
        total_days = sum(n for _, n in mw)
        for wk, n in mw:
            weeks[wk]["spend"][cat] += amount * n / total_days
    return len(rows)


# ------------------------------------------------------------------ main

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="~/.config/coding-stats/config.json")
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--out", default=os.path.join(repo_root, "src", "data", "coding-stats.json"))
    args = ap.parse_args()

    with open(expand(args.config), encoding="utf-8") as fh:
        user = json.load(fh)
        cfg = {**DEFAULTS, **user}
        cfg["exclude"] = DEFAULTS["exclude"] + list(user.get("exclude", []))
    if not cfg.get("repos"):
        sys.exit("config: 'repos' must list at least one local checkout")

    weeks: dict[str, dict] = defaultdict(new_week)
    nrepos, web = collect_git(cfg, weeks)
    nfiles = collect_transcripts(cfg, weeks)
    nchores = collect_chores(cfg, weeks)
    nspend = collect_spend(cfg, weeks)

    # Fill every week from `since` to today so charts have a continuous axis.
    start = dt.date.fromisoformat(week_key(dt.date.fromisoformat(cfg["since"])))
    today = dt.date.today()
    d = start
    while d <= today:
        weeks[d.isoformat()]  # touch
        d += dt.timedelta(days=7)

    rows = []
    for wk in sorted(weeks):
        if wk < start.isoformat():
            continue
        w = weeks[wk]
        w["claude_minutes"] = round(w["claude_minutes"])
        w["spend"] = {k: round(v, 2) for k, v in w["spend"].items()}
        rows.append({"week": wk, **w})

    out = {
        "generated": today.isoformat(),
        "since": cfg["since"],
        "web_session_minutes": est_or(cfg),
        "idle_gap_minutes": cfg["idle_gap_minutes"],
        "chore_categories": CHORE_CATEGORIES,
        "spend_categories": SPEND_CATEGORIES,
        "weeks": rows,
    }
    os.makedirs(os.path.dirname(expand(args.out)) or ".", exist_ok=True)
    with open(expand(args.out), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")
    print(f"wrote {args.out}: {len(rows)} weeks from {nrepos} repos, "
          f"{nfiles} transcript files, {len(web)} web sessions, "
          f"{nchores} chores, {nspend} spend rows", file=sys.stderr)


def est_or(cfg: dict) -> int:
    return int(cfg["web_session_minutes"])


if __name__ == "__main__":
    main()
