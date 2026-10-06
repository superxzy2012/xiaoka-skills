#!/usr/bin/env python3
"""Audit who is who in a Feishu chat using only the local gateway logs.

Read-only, stdlib only, touches no credentials. For each inbound group message it
extracts the `[Mentioned: ...]` prefix, the sender id, and the chat id, then reports:

  * name -> open_id pairs with hit counts across all log files
  * sender counts split by user: / bot:
  * open_ids @-mentioned more than once inside one message (duplicate @ spam)
  * heads whose mention list was truncated mid-id (NOT missing members)

    python3 scripts/feishu_roster_audit.py                       # default log set
    python3 scripts/feishu_roster_audit.py a.log b.log.1 --json

An id seen only once, in a truncated head, is NOT proof of membership -- confirm
outbound with scripts/feishu_mention_probe.py and judge by mentions[].
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

DEFAULT_LOGS = [
    "/opt/data/logs/gateway.log",
    "/opt/data/logs/gateway.log.1",
    "/opt/data/logs/agent.log",
    "/opt/data/logs/agent.log.1",
]

INBOUND = "Inbound group message received"
# name immediately followed by "(open_id=ou_...)" -- the closing paren is required so a
# width-truncated trailing id is NOT counted as a confirmed pair.
PAIR = re.compile(r"([^\(\],:]+?)\s*\(open_id=(ou_[0-9a-f]+)\)")
ANY_ID = re.compile(r"open_id=(ou_[0-9a-f]+)")
CHAT = re.compile(r"chat_id=(oc_[a-f0-9]+)")
SENDER = re.compile(r"sender=(\w+):(ou_[a-f0-9]+)")


def expand(paths):
    out = []
    for p in paths:
        hits = sorted(glob.glob(p))
        out.extend(hits or ([p] if os.path.exists(p) else []))
    return out


def audit(paths):
    pairs = collections.Counter()
    senders = collections.Counter()
    chats = collections.Counter()
    dupes = collections.Counter()
    truncated = []
    for path in expand(paths):
        with open(path, errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                if INBOUND not in line and "Mentioned:" not in line:
                    continue
                sm = SENDER.search(line)
                if sm:
                    senders[(sm.group(1), sm.group(2))] += 1
                cm = CHAT.search(line)
                if cm:
                    chats[cm.group(1)] += 1
                if "Mentioned:" not in line:
                    continue
                head = line.split("Mentioned:", 1)[1]
                ids = ANY_ID.findall(head)
                seen_in_msg = collections.Counter(PAIR.findall(head))
                for (name, oid), n in seen_in_msg.items():
                    pairs[(name.strip(), oid)] += n
                for oid, n in collections.Counter(ids).items():
                    if n > 1:
                        dupes[oid] += 1
                # A trailing id with no closing paren == the log cut the head off.
                if ids and not PAIR.findall(head) or (
                    ids and head.rstrip().rstrip("'").endswith(tuple("0123456789abcdef"))
                    and not head.rstrip().rstrip("'").endswith(")")
                ):
                    truncated.append((path, lineno, head.strip()[-70:]))
    return {
        "pairs": [{"name": n, "open_id": o, "hits": c} for (n, o), c in pairs.most_common()],
        "senders": [{"kind": k, "open_id": o, "hits": c} for (k, o), c in senders.most_common()],
        "chats": [{"chat_id": c, "messages": n} for c, n in chats.most_common()],
        "duplicate_mentions": [{"open_id": o, "messages": n} for o, n in dupes.most_common()],
        "possibly_truncated": truncated,
    }


def render(rep):
    print("== name -> open_id (hits across logs) ==")
    for r in rep["pairs"] or [{"name": "(none)", "open_id": "-", "hits": 0}]:
        print("  %-28s %s  %d" % (r["name"][:28], r["open_id"], r["hits"]))
    print("\n== senders ==")
    for r in rep["senders"] or [{"kind": "(none)", "open_id": "-", "hits": 0}]:
        print("  %-5s %s  %d" % (r["kind"], r["open_id"], r["hits"]))
    print("\n== chats ==")
    for r in rep["chats"]:
        print("  %s  %d msgs" % (r["chat_id"], r["messages"]))
    if rep["duplicate_mentions"]:
        print("\n== duplicate @s in one message (event fires per occurrence) ==")
        for r in rep["duplicate_mentions"]:
            print("  %s in %d message(s)" % (r["open_id"], r["messages"]))
    if rep["possibly_truncated"]:
        print("\n== heads truncated mid-id (NOT missing members) ==")
        for path, lineno, tail in rep["possibly_truncated"]:
            print("  %s:%d ...%s" % (path, lineno, tail))
    print(
        "\nSingle-hit ids are unproven. Confirm outbound with feishu_mention_probe.py and\n"
        "judge by mentions[], not by code:0. Resolve your own id via /open-apis/bot/v3/info."
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("logs", nargs="*", default=DEFAULT_LOGS, help="log paths or globs")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    a = ap.parse_args()
    rep = audit(a.logs or DEFAULT_LOGS)
    if a.json:
        json.dump(rep, sys.stdout, ensure_ascii=False, indent=2)
        print()
    else:
        render(rep)
    return 0


if __name__ == "__main__":
    sys.exit(main())