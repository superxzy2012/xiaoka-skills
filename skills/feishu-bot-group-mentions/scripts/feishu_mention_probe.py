#!/usr/bin/env python3
"""Feishu mention probe: send an @ and prove it parsed, or recall / inspect a chat.

Credentials are read from an env file (default /opt/data/.env) and never inlined,
so this script stays safe to archive, sync, and share.

Modes:
  --send <chat_id> <open_id> <text>   send <at> + text, report mentions[]
  --recall <message_id>               DELETE a sent message
  --chat-info <chat_id>               prove app identity + bot presence (bot_count)
  --list-members <chat_id>            needs im:chat:readonly

Exit codes: 0 verified / 3 sent but mentions empty / 1 API error.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

OPEN = "https://open.feishu.cn/open-apis"
TOKEN_URL = OPEN + "/auth/v3/tenant_access_token/internal"
SEND_URL = OPEN + "/im/v1/messages?receive_id_type=chat_id"
DEFAULT_ENV = "/opt/data/.env"


def load_env(path):
    env = {}
    if not os.path.exists(path):
        sys.exit("env file not found: %s" % path)
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key] = val.strip().strip('"').strip("'")
    return env


def call(url, payload=None, token=None, method=None):
    """Return the parsed JSON body. urllib raises on 4xx, so pull the body off the error."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        raw = urllib.request.urlopen(req, timeout=20).read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
    try:
        return json.loads(raw)
    except ValueError:
        sys.exit("unparsable response: %r" % raw[:300])


def tenant_token(env):
    res = call(
        TOKEN_URL,
        {
            "app_id": env.get("FEISHU_APP_ID", ""),
            "app_secret": env.get("FEISHU_APP_SECRET", ""),
        },
    )
    if res.get("code") != 0:
        sys.exit("token failed: %s" % res.get("msg"))
    return res["tenant_access_token"]


def do_send(token, chat_id, open_id, text):
    # A plain-text "@name" is NOT a mention; only the tag parses into mentions[].
    body = '<at user_id="%s"></at> %s' % (open_id, text)
    res = call(
        SEND_URL,
        {
            "receive_id": chat_id,
            "msg_type": "text",
            "content": json.dumps({"text": body}, ensure_ascii=False),
        },
        token=token,
    )
    print("code=%s msg=%s" % (res.get("code"), res.get("msg")))
    if res.get("code") != 0:
        return 1
    data = res.get("data") or {}
    print("message_id=%s" % data.get("message_id"))
    mentions = data.get("mentions") or []
    for m in mentions:
        print("mention ok -> %s %s" % (m.get("name"), m.get("id")))
    if not mentions:
        print("mentions=[]  <-- @ did NOT parse: wrong app-view open_id, or target not in chat")
        return 3
    return 0


def do_recall(token, message_id):
    res = call(OPEN + "/im/v1/messages/" + message_id, {}, token=token, method="DELETE")
    print("recall code=%s msg=%s" % (res.get("code"), res.get("msg")))
    return 0 if res.get("code") == 0 else 1


def do_chat_info(token, chat_id):
    res = call(OPEN + "/im/v1/chats/" + chat_id, token=token)
    print("code=%s msg=%s" % (res.get("code"), res.get("msg")))
    data = res.get("data") or {}
    if res.get("code") == 0:
        print(
            "name=%s bot_count=%s chat_status=%s"
            % (data.get("name"), data.get("bot_count"), data.get("chat_status"))
        )
        return 0
    return 1


def do_list_members(token, chat_id):
    url = OPEN + "/im/v1/chats/" + chat_id + "/members?member_id_type=open_id&page_size=100"
    res = call(url, token=token)
    print("code=%s msg=%s" % (res.get("code"), res.get("msg")))
    if res.get("code") != 0:
        if res.get("code") == 99991672:
            print(
                "missing im:chat:readonly - do not open it for this; read the id from the "
                "inbound log's [Mentioned: ...] prefix instead"
            )
        return 1
    for item in (res.get("data") or {}).get("items", []):
        print("  %s %s" % (item.get("member_id"), item.get("name")))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--send", nargs=3, metavar=("CHAT_ID", "OPEN_ID", "TEXT"))
    group.add_argument("--recall", metavar="MESSAGE_ID")
    group.add_argument("--chat-info", metavar="CHAT_ID")
    group.add_argument("--list-members", metavar="CHAT_ID")
    args = ap.parse_args()

    token = tenant_token(load_env(args.env_file))
    if args.send:
        return do_send(token, *args.send)
    if args.recall:
        return do_recall(token, args.recall)
    if getattr(args, "chat_info", None):
        return do_chat_info(token, args.chat_info)
    return do_list_members(token, args.list_members)


if __name__ == "__main__":
    sys.exit(main())