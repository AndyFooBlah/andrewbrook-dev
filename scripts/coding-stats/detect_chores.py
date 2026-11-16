#!/usr/bin/env python3
"""Find manual chores in Claude Code transcripts and append them to a ledger.

A chore is a hands-on task the agent handed back to you because it could not
do it itself: run this command in your terminal, click through a cloud
console, paste a secret, approve an OAuth screen, test it on your phone.
Decisions, approvals and requests for information are not chores.

Which messages are read: the agent's last message before you next spoke (or
before the session ended). Messages followed by a background-task
notification, a system reminder or another session's message are skipped,
because the agent restates anything still pending when it next reports to
you. Subagent transcripts are skipped; their reader is another agent.

How a chore is recognised, in order:
  1. The message carries a ready-made `chore <category> <minutes> "<note>"`
     line (agents are asked to end hand-backs with one). Taken as written.
  2. Otherwise a small Gemini model on Vertex AI (in your own Google Cloud
     project; the messages go nowhere else) lists every request in the
     message and labels its kind; only `manual_action` requests are kept.

Each message is recorded in the ledger by uuid, chore or not, so it is never
read twice. A network failure skips that batch and leaves it for the next run.

Usage:
  detect_chores.py [--config ~/.config/coding-stats/config.json] [--limit N] [--dry-run]

Config keys (see README.md): transcripts, since, auto_ledger, chore_detector
  {"project": "...", "location": "global", "model": "gemini-3.5-flash-lite"}.
Needs `gcloud auth application-default login` once, and Vertex AI enabled
on the project.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

LEDGER_VERSION = 2   # rows from an older detector are ignored and their messages re-read
CATEGORIES = ["terminal", "cloud-infra", "secrets-auth", "accounts-billing", "dns-deploy",
              "manual-testing", "other"]
KINDS = ["manual_action", "decision", "information", "optional"]
BATCH = 12          # messages per model call
MAX_CHARS = 6000    # per message; hand-backs are near the end, so keep the tail
MAX_MINUTES = 60

DECLARED = re.compile(
    r'^[\s`>*-]*chore\s+(' + "|".join(CATEGORIES) + r')\s+(\d+)\s+"([^"\n]*)"', re.M)
REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)

PROMPT = """You are auditing transcripts of coding agents that work for one developer, the owner.
Each numbered message below is the last thing an agent said before the owner next spoke.
List every request the message makes of the owner, and label each with a kind:

- manual_action: a concrete hands-on task the agent could not do itself and is handing to the
  owner. The category says which:
    terminal: run a command in the owner's own terminal and report or paste the result
    cloud-infra: click through a cloud, Firebase, GitHub or admin console to change a setting
    secrets-auth: provide or rotate a secret or key, sign in, pass 2FA, approve an OAuth or consent screen
    accounts-billing: create an account, sign up, change billing, plan or quota
    dns-deploy: change DNS, domain, hosting or app-store settings
    manual-testing: try the thing on a device or in a browser and report back
    other: any other hands-on task only the owner can do
- decision: the owner is asked to choose, approve, confirm, rule on, review, prioritise or give
  a go-ahead. "Merge this PR", "pick option A or B", "confirm the budget", "review the draft"
  and "say the word and I'll start the run" are all decisions.
- information: the owner is asked for facts, numbers, preferences or files they already know or have.
- optional: an offer or suggestion the owner may ignore, or something the agent will do itself.

Only manual_action requests are chores, so be strict: when a request could be manual_action or
another kind, choose the other kind. Do not list work the agent already did, explanations or advice.
For minutes, estimate the owner's own hands-on time (2 to 60), not time spent waiting.
The note is at most 8 words and never includes secrets, keys or URLs.

Return JSON: an array with one object per message index that makes at least one request:
{"index": <int>, "requests": [{"kind": ..., "category": ..., "minutes": <int>, "note": "..."}]}.
Messages that make no request are omitted. Return [] if none.

Messages:
"""

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "index": {"type": "INTEGER"},
            "requests": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "kind": {"type": "STRING", "enum": KINDS},
                        "category": {"type": "STRING", "enum": CATEGORIES},
                        "minutes": {"type": "INTEGER"},
                        "note": {"type": "STRING"},
                    },
                    "required": ["kind", "category", "minutes", "note"],
                },
            },
        },
        "required": ["index", "requests"],
    },
}


def expand(p: str) -> str:
    return os.path.expanduser(os.path.expandvars(p))


def text_of(msg: dict) -> str:
    c = msg.get("message", {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def is_tool_result(msg: dict) -> bool:
    c = msg.get("message", {}).get("content")
    return isinstance(c, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c)


def from_owner(msg: dict) -> bool:
    """True when a user-role record is the owner acting, not an automated wake-up."""
    if msg.get("type") != "user" or is_tool_result(msg):
        return False
    origin = msg.get("origin")
    if isinstance(origin, dict) and origin.get("kind"):
        return origin["kind"] == "human"
    if msg.get("isMeta"):                      # the owner ran a local command (/model, a shell line)
        return True
    text = REMINDER.sub("", text_of(msg)).strip()
    return bool(text) and not text.startswith("<task-notification")


def candidate_messages(roots: list[str], since: str) -> list[dict]:
    """The agent's last message before the owner next spoke, one per uuid.

    Forked and resumed sessions copy earlier messages into a new file, so the
    same uuid turns up in several files; it qualifies if it does in any.
    """
    out: dict[str, dict] = {}
    for root in roots:
        for path in glob.glob(os.path.join(expand(root), "**", "*.jsonl"), recursive=True):
            if f"{os.sep}subagents{os.sep}" in path:
                continue
            msgs = []
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") in ("user", "assistant") and "timestamp" in o and not o.get("isSidechain"):
                        msgs.append(o)
            owner_present = any(from_owner(m) for m in msgs)
            for i, o in enumerate(msgs):
                if o["type"] != "assistant" or o["timestamp"][:10] < since:
                    continue
                uuid = o.get("uuid")
                if not uuid or uuid in out:
                    continue
                nxt = msgs[i + 1] if i + 1 < len(msgs) else None
                if not (from_owner(nxt) if nxt is not None else owner_present):
                    continue
                txt = text_of(o).strip()
                if len(txt) < 40:
                    continue
                out[uuid] = {"uuid": uuid, "timestamp": o["timestamp"], "text": txt,
                             "session": o.get("sessionId") or os.path.basename(path)}
    return sorted(out.values(), key=lambda m: m["timestamp"])


def access_token() -> str:
    r = subprocess.run(["gcloud", "auth", "application-default", "print-access-token"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("gcloud ADC token failed; run: gcloud auth application-default login\n" + r.stderr)
    return r.stdout.strip()


def classify(batch: list[dict], det: dict, token: str) -> list[dict] | None:
    """Requests per message index, or None when the call failed and the batch should be retried later."""
    parts = [PROMPT]
    for i, m in enumerate(batch):
        parts.append(f"\n--- message {i} ---\n{m['text'][-MAX_CHARS:]}\n")
    loc = det.get("location", "global")
    host = "aiplatform.googleapis.com" if loc == "global" else f"{loc}-aiplatform.googleapis.com"
    url = (f"https://{host}/v1/projects/{det['project']}/locations/{loc}"
           f"/publishers/google/models/{det['model']}:generateContent")
    body = {
        "contents": [{"role": "user", "parts": [{"text": "".join(parts)}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json",
                             "responseSchema": SCHEMA},
    }
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"})
    data, err = None, ""
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.read().decode(errors='replace')[:300]}"
            if e.code not in (429, 500, 502, 503, 504):
                break
        except (urllib.error.URLError, TimeoutError, OSError) as e:   # DNS, reset, read timeout
            err = f"{type(e).__name__}: {e}"
        time.sleep(2 ** attempt * 3)
    if data is None:
        print(f"warning: Vertex AI call failed, batch left for the next run ({err})", file=sys.stderr)
        return None
    try:
        result = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"warning: unparseable model response ({e}); batch left for the next run", file=sys.stderr)
        return None
    return result if isinstance(result, list) else []


def chore_row(m: dict, category: str, minutes: int, note: str, source: str) -> dict:
    return {"date": m["timestamp"][:10], "category": category,
            "minutes": max(1, min(int(minutes or 5), MAX_MINUTES)), "note": str(note)[:120],
            "uuid": m["uuid"], "session": m["session"], "source": source, "v": LEDGER_VERSION}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="~/.config/coding-stats/config.json")
    ap.add_argument("--limit", type=int, default=0, help="read at most N new messages")
    ap.add_argument("--dry-run", action="store_true", help="print chores instead of appending")
    args = ap.parse_args()
    with open(expand(args.config), encoding="utf-8") as fh:
        cfg = json.load(fh)
    det = cfg.get("chore_detector")
    if not det or not det.get("project"):
        sys.exit("config: chore_detector.project is required")
    det.setdefault("model", "gemini-3.5-flash-lite")
    ledger = expand(cfg.get("auto_ledger", "~/.config/coding-stats/chores-auto.jsonl"))
    since = cfg.get("since", "2025-01-01")

    seen: set[str] = set()
    if os.path.exists(ledger):
        with open(ledger, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if row.get("v") == LEDGER_VERSION:
                        seen.add(row.get("uuid", ""))
    msgs = [m for m in candidate_messages(cfg.get("transcripts", ["~/.claude/projects"]), since)
            if m["uuid"] not in seen]
    if args.limit:
        msgs = msgs[-args.limit:]
    print(f"{len(msgs)} new messages to read ({len(seen)} already seen)", file=sys.stderr)
    if not msgs:
        return 0

    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    out = sys.stdout if args.dry_run else open(ledger, "a", encoding="utf-8")
    found = failed = 0

    def record(m: dict, rows: list[dict]) -> None:
        nonlocal found
        found += len(rows)
        if not rows and not args.dry_run:
            rows = [{"date": m["timestamp"][:10], "uuid": m["uuid"], "none": True, "v": LEDGER_VERSION}]
        for row in rows:
            out.write(json.dumps(row) + "\n")

    try:
        undeclared = []
        for m in msgs:
            lines = DECLARED.findall(m["text"])
            if lines:
                record(m, [chore_row(m, cat, int(mins), note, "declared") for cat, mins, note in lines])
            else:
                undeclared.append(m)
        print(f"  {len(msgs) - len(undeclared)} messages carried a chore line, {found} chores", file=sys.stderr)
        token = access_token() if undeclared else ""
        for start in range(0, len(undeclared), BATCH):
            batch = undeclared[start:start + BATCH]
            result = classify(batch, det, token)
            if result is None:
                failed += 1
                continue
            hits = {h.get("index"): h.get("requests", []) for h in result if isinstance(h, dict)}
            for i, m in enumerate(batch):
                record(m, [chore_row(m, r["category"], r.get("minutes", 5), r.get("note", ""), "auto")
                           for r in hits.get(i, [])
                           if r.get("kind") == "manual_action" and r.get("category") in CATEGORIES])
            out.flush()
            done = min(start + BATCH, len(undeclared))
            if done % (BATCH * 10) == 0 or done == len(undeclared):
                print(f"  {done}/{len(undeclared)} classified, {found} chores so far", file=sys.stderr)
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"{found} chores {'found' if args.dry_run else 'appended to ' + ledger}"
          + (f"; {failed} batch(es) failed and will be retried next run" if failed else ""), file=sys.stderr)
    return 1 if failed and not found else 0


if __name__ == "__main__":
    sys.exit(main())
