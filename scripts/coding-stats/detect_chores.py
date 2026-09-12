#!/usr/bin/env python3
"""Find manual chores in Claude Code transcripts and append them to a ledger.

A chore is a task the agent handed back to you because it could not do it
itself: run this command in your terminal, click through a cloud console,
paste a secret, approve an OAuth screen, test it on your phone. The last
assistant message of every turn is classified by a small Gemini model on
Vertex AI (the messages never leave your own Google Cloud project), and each
chore found is appended to the auto ledger with the message's uuid so a
message is never classified twice.

Usage:
  detect_chores.py [--config ~/.config/coding-stats/config.json] [--limit N] [--dry-run]

Config keys (see README.md): transcripts, since, auto_ledger, chore_detector
  {"project": "...", "location": "global", "model": "gemini-3.5-flash-lite"}.
Needs `gcloud auth application-default login` once, and Vertex AI enabled
on the project.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

CATEGORIES = ["terminal", "cloud-infra", "secrets-auth", "accounts-billing", "dns-deploy",
              "manual-testing", "other"]
BATCH = 12          # messages per model call
MAX_CHARS = 6000    # per message; hand-backs are near the end, so keep the tail

PROMPT = """You are auditing transcripts of a coding agent working for one developer.
For each numbered assistant message below, decide whether the agent is HANDING A TASK BACK
to the developer because the agent could not do it itself. Count it only when the message
asks the developer to personally do something like:
- terminal: run a command in their own terminal (restart a program, run a script, paste output)
- cloud-infra: click through a cloud, Firebase, GitHub, or admin console (enable an API, change a setting)
- secrets-auth: provide or rotate a secret, API key, token, password, 2FA, log in, or approve an OAuth/consent screen
- accounts-billing: create an account, sign up, change billing, plan, or quota
- dns-deploy: change DNS, domain, hosting/Pages settings, or app-store/TestFlight settings
- manual-testing: try the thing on a device or browser and report back

Do NOT count: summaries of work already done, explanations, commands the agent already ran,
questions about preferences or design, requests for information, numbers, or decisions,
offers ("say the word and I'll..."), or advice.
A message may contain several chores; report each separately.

Return JSON: an array with one object per message index that contains at least one chore:
{"index": <int>, "chores": [{"category": <one of %s>, "minutes": <estimated minutes for
the developer, 2-60>, "note": "<at most 8 words; never include secrets, keys, or URLs>"}]}.
Messages with no chore are omitted. Return [] if none.

Messages:
""" % CATEGORIES

SCHEMA = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "index": {"type": "INTEGER"},
            "chores": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "category": {"type": "STRING", "enum": CATEGORIES},
                        "minutes": {"type": "INTEGER"},
                        "note": {"type": "STRING"},
                    },
                    "required": ["category", "minutes", "note"],
                },
            },
        },
        "required": ["index", "chores"],
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


def turn_final_messages(roots: list[str], since: str) -> list[dict]:
    """Assistant messages that end a turn (next message is a human prompt, or EOF)."""
    out = []
    for root in roots:
        for path in glob.glob(os.path.join(expand(root), "**", "*.jsonl"), recursive=True):
            msgs = []
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if o.get("type") in ("user", "assistant") and "timestamp" in o:
                        msgs.append(o)
            for i, o in enumerate(msgs):
                if o["type"] != "assistant" or o["timestamp"][:10] < since:
                    continue
                nxt = msgs[i + 1] if i + 1 < len(msgs) else None
                if nxt is not None and (nxt["type"] != "user" or is_tool_result(nxt)):
                    continue
                txt = text_of(o).strip()
                if len(txt) < 40:
                    continue
                out.append({"uuid": o.get("uuid") or f"{path}:{i}", "timestamp": o["timestamp"], "text": txt})
    out.sort(key=lambda m: m["timestamp"])
    return out


def access_token() -> str:
    r = subprocess.run(["gcloud", "auth", "application-default", "print-access-token"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("gcloud ADC token failed; run: gcloud auth application-default login\n" + r.stderr)
    return r.stdout.strip()


def classify(batch: list[dict], det: dict, token: str) -> list[dict]:
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
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.load(resp)
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 3:
                import time
                time.sleep(2 ** attempt * 3)
                continue
            sys.exit(f"Vertex AI error {e.code}: {e.read().decode()[:500]}")
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"warning: unparseable model response ({e}); skipping batch", file=sys.stderr)
        return []
    return result if isinstance(result, list) else []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default="~/.config/coding-stats/config.json")
    ap.add_argument("--limit", type=int, default=0, help="classify at most N new messages")
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
                        seen.add(json.loads(line).get("uuid", ""))
                    except json.JSONDecodeError:
                        pass
    # A message with no chore is recorded as a marker row so it is not re-sent.
    msgs = [m for m in turn_final_messages(cfg.get("transcripts", ["~/.claude/projects"]), since)
            if m["uuid"] not in seen]
    if args.limit:
        msgs = msgs[:args.limit]
    print(f"{len(msgs)} new turn-final messages to classify ({len(seen)} already seen)", file=sys.stderr)
    if not msgs:
        return

    token = access_token()
    os.makedirs(os.path.dirname(ledger), exist_ok=True)
    found = 0
    out = sys.stdout if args.dry_run else open(ledger, "a", encoding="utf-8")
    try:
        for start in range(0, len(msgs), BATCH):
            batch = msgs[start:start + BATCH]
            hits = {h["index"]: h.get("chores", []) for h in classify(batch, det, token)}
            for i, m in enumerate(batch):
                date = m["timestamp"][:10]
                chores = [c for c in hits.get(i, []) if c.get("category") in CATEGORIES]
                if not chores:
                    if not args.dry_run:
                        out.write(json.dumps({"date": date, "uuid": m["uuid"], "none": True}) + "\n")
                    continue
                for c in chores:
                    found += 1
                    row = {"date": date, "category": c["category"],
                           "minutes": max(1, min(int(c.get("minutes", 5)), 240)),
                           "note": str(c.get("note", ""))[:80], "uuid": m["uuid"], "source": "auto"}
                    out.write(json.dumps(row) + "\n")
            out.flush()
            print(f"  {min(start + BATCH, len(msgs))}/{len(msgs)} classified, {found} chores so far", file=sys.stderr)
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"{found} chores {'found' if args.dry_run else 'appended to ' + ledger}", file=sys.stderr)


if __name__ == "__main__":
    main()
