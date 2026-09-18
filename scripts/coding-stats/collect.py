#!/usr/bin/env python3
"""Aggregate AI-vs-hand coding stats into one anonymised weekly JSON file.

Sources (all read locally, nothing leaves the machine except the output):

  git repos      lines/commits per week, split AI vs hand by the
                 "Co-Authored-By: Claude" trailer that Claude Code writes.
  transcripts    ~/.claude/projects/**/*.jsonl -> active minutes with Claude,
                 plus Gemini CLI chats and the Antigravity CLI prompt history
                 where they exist, for the same measures.
  chores.jsonl   manual tasks you logged (scripts/coding-stats/chore.sh).
  chores-auto.jsonl  tasks the agent handed back to you, found in the
                 transcripts by scripts/coding-stats/detect_chores.py.
  spend.jsonl    subscription, top-ups, cloud bills -> dollars per week.

The output contains ONLY weekly totals (plus token counts per model). No
repo names, paths, session ids, commit messages or chore notes are ever
written to it.

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
    "terminal",         # a command to run in your own terminal
    "cloud-infra",      # console/CLI changes in GCP, AWS, etc.
    "secrets-auth",     # keys, OAuth consent screens, tokens, 2FA
    "accounts-billing", # sign-ups, billing, quotas, plan changes
    "dns-deploy",       # DNS, Pages settings, app-store style releases
    "manual-testing",   # clicking through the thing to see if it works
    "other",
]
SPEND_CATEGORIES = ["claude", "jev", "cloud", "other"]

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
    "gemini_transcripts": ["~/.gemini/tmp"],          # Gemini CLI **/chats/*.jsonl
    "antigravity_history": "~/.gemini/antigravity-cli/history.jsonl",
    "idle_gap_minutes": 15,
    "web_session_minutes": 30,     # estimate per remote (claude.ai/code) session
    "ledger": "~/.config/coding-stats/chores.jsonl",
    "auto_ledger": "~/.config/coding-stats/chores-auto.jsonl",  # written by detect_chores.py
    "spend": "~/.config/coding-stats/spend.jsonl",
    "spend_auto": "~/.config/coding-stats/spend-auto.jsonl",   # written by collectors below
    # Automatic spend sources; see README. Each is optional.
    "subscriptions": [],           # [{"category","amount","since","until","note"}]
    "gcp_billing_export": None,    # {"project","dataset"} holding gcp_billing_export_v1_* tables
    # Jev (TypeSafe) calls go through a Cloud Run proxy that logs each request
    # with its cost; {"project","service"}. Logs expire, so days are persisted
    # into `spend_auto`.
    "jev_proxy_logs": None,
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
        "tokens": {},   # model id -> {input, output, cache_read, cache_write}
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
    min(gap, idle_gap). Assistant messages also carry the model and token
    counts, summed per week and model. Returns number of transcript files read.
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
                    usage = o.get("message", {}).get("usage") if o["type"] == "assistant" else None
                    model = o.get("message", {}).get("model", "")
                    if usage and model and not model.startswith("<"):
                        tk = weeks[week_key(ts.date())]["tokens"].setdefault(
                            model, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
                        tk["input"] += usage.get("input_tokens") or 0
                        tk["output"] += usage.get("output_tokens") or 0
                        tk["cache_read"] += usage.get("cache_read_input_tokens") or 0
                        tk["cache_write"] += usage.get("cache_creation_input_tokens") or 0
                    sid = o.get("sessionId") or path
                    if sid not in session_start or ts < session_start[sid]:
                        session_start[sid] = ts
    files += collect_gemini(cfg, weeks, points, session_start, since)
    points.sort()
    for a, b in zip(points, points[1:]):
        gap = (b - a).total_seconds()
        weeks[week_key(a.date())]["claude_minutes"] += min(gap, gap_cap) / 60.0
    for ts in session_start.values():
        weeks[week_key(ts.date())]["sessions"] += 1
    return files


def add_tokens(weeks: dict, ts: dt.datetime, model: str, inp: int, out: int, cread: int, cwrite: int) -> None:
    tk = weeks[week_key(ts.date())]["tokens"].setdefault(
        model, {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0})
    tk["input"] += inp
    tk["output"] += out
    tk["cache_read"] += cread
    tk["cache_write"] += cwrite


def collect_gemini(cfg: dict, weeks: dict, points: list, session_start: dict, since: dt.datetime) -> int:
    """Gemini CLI chat logs and the Antigravity CLI prompt history.

    Gemini CLI writes one JSONL per session under <root>/**/chats/ with
    `user` and `gemini` records; `gemini` records carry the model and a
    tokens block (input includes cached; thoughts are output). Antigravity
    CLI keeps only a prompt history with millisecond timestamps, so it adds
    activity time and sessions but no tokens. Returns files read.
    """
    files = 0
    for root in cfg["gemini_transcripts"]:
        for path in glob.glob(os.path.join(expand(root), "**", "chats", "*.jsonl"), recursive=True):
            files += 1
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") not in ("user", "gemini") or "timestamp" not in o:
                        continue
                    try:
                        ts = parse_ts(o["timestamp"])
                    except ValueError:
                        continue
                    if ts < since:
                        continue
                    points.append(ts)
                    sid = "gemini:" + path
                    if sid not in session_start or ts < session_start[sid]:
                        session_start[sid] = ts
                    t, model = o.get("tokens") or {}, o.get("model")
                    if o["type"] == "gemini" and t and model:
                        cached = int(t.get("cached") or 0)
                        add_tokens(weeks, ts, model, max(int(t.get("input") or 0) - cached, 0),
                                   int(t.get("output") or 0) + int(t.get("thoughts") or 0), cached, 0)
    hist = expand(cfg["antigravity_history"])
    if os.path.exists(hist):
        files += 1
        with open(hist, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "timestamp" not in o:
                    continue
                ts = dt.datetime.fromtimestamp(o["timestamp"] / 1000, tz=dt.timezone.utc)
                if ts < since:
                    continue
                points.append(ts)
                sid = "antigravity:" + str(o.get("conversationId") or ts.date())
                if sid not in session_start or ts < session_start[sid]:
                    session_start[sid] = ts
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
    rows = [r for r in read_jsonl(cfg["ledger"]) + read_jsonl(cfg["auto_ledger"])
            if not r.get("none")]   # the auto ledger marks chore-free messages too
    # The same hand-back restated in consecutive messages should count once.
    seen: set[tuple] = set()
    rows = [r for r in rows
            if (k := (r["date"], r.get("category"), r.get("note", ""))) not in seen and not seen.add(k)]
    for r in rows:
        cat = r.get("category", "other")
        if cat not in CHORE_CATEGORIES:
            sys.exit(f"chores: unknown category {cat!r}; use one of {CHORE_CATEGORIES}")
        wk = weeks[week_key(dt.date.fromisoformat(r["date"]))]
        wk["chores"][cat] += 1
        wk["chore_minutes"] += int(r.get("minutes", 0))
    return len(rows)


def month_range(period: str) -> tuple[dt.date, dt.date]:
    y, m = (int(x) for x in period.split("-"))
    return dt.date(y, m, 1), dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)


def range_weeks(first: dt.date, last: dt.date) -> list[tuple[str, int]]:
    """(week_key, days-of-that-week-inside-range) for an inclusive day range."""
    counts: dict[str, int] = defaultdict(int)
    d = first
    while d <= last:
        counts[week_key(d)] += 1
        d += dt.timedelta(days=1)
    return list(counts.items())


def subscription_rows(cfg: dict, today: dt.date) -> list[dict]:
    """One charge per billing cycle for each flat-rate subscription.

    Charges land on the day-of-month of `since` (clamped to the month's
    length) from `since` until `until` or today, and each covers the days
    from that charge to the day before the next one.
    """
    rows = []
    floor = dt.date.fromisoformat(cfg["since"])
    for sub in cfg["subscriptions"]:
        start = dt.date.fromisoformat(sub["since"])
        end = dt.date.fromisoformat(sub["until"]) if sub.get("until") else today
        y, m = start.year, start.month
        while True:
            last = (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)).day
            charge = dt.date(y, m, min(start.day, last))
            if charge > end:
                break
            y, m = (y + (m == 12), (m % 12) + 1)
            last = (dt.date(y + (m == 12), (m % 12) + 1, 1) - dt.timedelta(days=1)).day
            cycle_end = dt.date(y, m, min(start.day, last)) - dt.timedelta(days=1)
            if sub.get("until"):
                cycle_end = min(cycle_end, end)
            if charge >= floor:
                rows.append({"date": charge.isoformat(), "start": charge.isoformat(),
                             "end": cycle_end.isoformat(),
                             "amount": sub["amount"], "category": sub.get("category", "other")})
    return rows


def collect_gcp_billing(cfg: dict, weeks: dict) -> int:
    """Net daily cost from a Cloud Billing BigQuery export, via the bq CLI.

    Reads every gcp_billing_export_v1_* table in the dataset (one per
    billing account), nets out credits, and books each day's cost to its
    week as "cloud" spend. Returns the number of days read.
    """
    src = cfg["gcp_billing_export"]
    if not src:
        return 0
    table = f"`{src['project']}.{src['dataset']}.gcp_billing_export_v1_*`"
    sql = f"""
        SELECT DATE(usage_start_time) AS day, currency,
               SUM(cost) + SUM(IFNULL((SELECT SUM(c.amount) FROM UNNEST(credits) c), 0)) AS net
        FROM {table}
        WHERE usage_start_time >= TIMESTAMP('{cfg["since"]}')
        GROUP BY day, currency ORDER BY day"""
    r = subprocess.run(["bq", "--project_id", src["project"], "--format=json", "--headless",
                        "query", "--use_legacy_sql=false", "--nouse_cache", "--max_rows=100000", sql],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("warning: GCP billing export query failed; cloud spend not updated:\n"
              + (r.stderr.strip() or r.stdout.strip()), file=sys.stderr)
        return 0
    rows = json.loads(r.stdout or "[]")
    for row in rows:
        if row["currency"] != "USD":
            sys.exit(f"gcp billing: unexpected currency {row['currency']}; the page assumes USD")
        weeks[week_key(dt.date.fromisoformat(row["day"]))]["spend"]["cloud"] += float(row["net"])
    return len(rows)


def upsert_auto_spend(cfg: dict, source: str, days: dict[str, float]) -> None:
    """Replace this source's rows for the given days in the auto spend ledger."""
    path = expand(cfg["spend_auto"])
    keep = [r for r in read_jsonl(cfg["spend_auto"])
            if not (r.get("source") == source and r["date"] in days)]
    for day, amount in sorted(days.items()):
        keep.append({"date": day, "start": day, "end": day, "category": "jev" if source == "jev-proxy" else "other",
                     "amount": round(amount, 6), "source": source})
    keep.sort(key=lambda r: (r["date"], r.get("source", "")))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in keep:
            fh.write(json.dumps(r) + "\n")


def collect_jev_logs(cfg: dict) -> int:
    """Daily Jev cost from the proxy's request log (jsonPayload.costUsd).

    The proxy computes cost from TypeSafe's list price per request. Cloud
    Logging keeps 30 days, so each run re-reads that window and rewrites
    those days in the auto ledger; older days stay as previously recorded.
    Returns the number of days updated.
    """
    src = cfg["jev_proxy_logs"]
    if not src:
        return 0
    flt = (f'resource.type="cloud_run_revision" AND resource.labels.service_name="{src["service"]}" '
           'AND jsonPayload.message="request" AND jsonPayload.provider="typesafe"')
    r = subprocess.run(["gcloud", "logging", "read", flt, "--project", src["project"], "--freshness=30d",
                        "--limit=100000", "--format=value(timestamp,jsonPayload.costUsd)"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("warning: Jev proxy log query failed; jev spend not updated:\n" + r.stderr.strip(), file=sys.stderr)
        return 0
    days: dict[str, float] = defaultdict(float)
    for line in r.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 2 and parts[1]:
            days[parts[0][:10]] += float(parts[1])
    # Days inside the window with no calls are recorded as zero so a stale
    # value from an earlier run cannot linger.
    start = dt.date.today() - dt.timedelta(days=29)
    for i in range(30):
        days.setdefault((start + dt.timedelta(days=i)).isoformat(), 0.0)
    upsert_auto_spend(cfg, "jev-proxy", dict(days))
    return sum(1 for v in days.values() if v)


def collect_spend(cfg: dict, weeks: dict, today: dt.date) -> int:
    """Spread each spend row across the weeks of its period.

    Rows come from the manual ledger plus generated subscription charges.
    A row covers its `period` month, or the `start`..`end` day range if
    given. Days after today are dropped and the amount pro-rated, so a
    half-elapsed billing cycle books half its charge. "claude" spend is
    spread in proportion to Claude activity (transcript minutes plus the
    web-session estimate) so idle weeks cost nothing; everything else
    (cloud bills etc.) is spread evenly by calendar day.
    """
    rows = read_jsonl(cfg["spend"]) + read_jsonl(cfg["spend_auto"]) + subscription_rows(cfg, today)
    est = cfg["web_session_minutes"]
    for r in rows:
        cat = r.get("category", "other")
        if cat not in SPEND_CATEGORIES:
            sys.exit(f"spend: unknown category {cat!r}; use one of {SPEND_CATEGORIES}")
        amount = float(r["amount"])
        if "start" in r:
            first, last = dt.date.fromisoformat(r["start"]), dt.date.fromisoformat(r["end"])
        else:
            first, last = month_range(r.get("period") or r["date"][:7])
        if first > today:
            continue
        if last > today:
            amount *= ((today - first).days + 1) / ((last - first).days + 1)
            last = today
        mw = range_weeks(first, last)
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
    today = dt.date.today()
    njev = collect_jev_logs(cfg)
    nspend = collect_spend(cfg, weeks, today)
    ndays = collect_gcp_billing(cfg, weeks)

    # Fill every week from `since` to today so charts have a continuous axis.
    start = dt.date.fromisoformat(week_key(dt.date.fromisoformat(cfg["since"])))
    d = start
    while d <= today:
        weeks[d.isoformat()]  # touch
        d += dt.timedelta(days=7)

    rows = []
    for wk in sorted(weeks):
        if wk < start.isoformat() or wk > week_key(today):
            continue
        w = weeks[wk]
        w["claude_minutes"] = round(w["claude_minutes"])
        w["spend"] = {k: round(v, 2) for k, v in w["spend"].items()}
        rows.append({"week": wk, **w})

    by_model: dict[str, int] = defaultdict(int)
    for r in rows:
        for model, tk in r["tokens"].items():
            by_model[model] += tk["output"]
    out = {
        "generated": today.isoformat(),
        "models": sorted(by_model, key=lambda m: -by_model[m]),   # by output tokens
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
          f"{nchores} chores, {nspend} spend rows, {njev} Jev days, {ndays} GCP billing days", file=sys.stderr)


def est_or(cfg: dict) -> int:
    return int(cfg["web_session_minutes"])


if __name__ == "__main__":
    main()
