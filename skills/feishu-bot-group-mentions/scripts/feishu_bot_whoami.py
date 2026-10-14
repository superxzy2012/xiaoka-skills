#!/usr/bin/env python3
"""Resolve THIS bot's own open_id + app_name via GET /open-apis/bot/v3/info.

Cheapest, scope-free way to learn who you are in a chat. Use it:
  * before a bot-to-bot handshake (you need your own id to hand out), and
  * when an inbound [Mentioned: ...] head appears to omit you -- it ALWAYS omits the
    receiving bot, so "I'm missing from the roster" is never a real finding.

Credentials are read from the env file and never inlined: probes get archived, synced and
shared, and a hardcoded app_secret leaks with them.

Usage:
    python3 scripts/feishu_bot_whoami.py [--env-file /opt/data/.env]

Prints app_name / open_id / activate_status. Exit 0 ok, 1 token or API error.
The id is app-scoped: it resolves for peers that share this app's view. A peer bot should
read your id from the sender=bot:ou_... field of your message in ITS own inbound log.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

OPEN = "https://open.feishu.cn/open-apis"
TOKEN_URL = OPEN + "/auth/v3/tenant_access_token/internal"
INFO_URL = OPEN + "/bot/v3/info"
DEFAULT_ENV = "/opt/data/.env"


def load_env(path):
    if not os.path.exists(path):
        sys.exit("env file not found: %s" % path)
    env = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key] = val.strip().strip('"').strip("'")
    return env


def call(url, payload=None, token=None):
    """Return the parsed JSON body; urllib raises on 4xx, so pull the body off the error."""
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        raw = urllib.request.urlopen(req, timeout=20).read()
    except urllib.error.HTTPError as exc:
        raw = exc.read()
    try:
        return json.loads(raw)
    except ValueError:
        sys.exit("unparsable response: %r" % raw[:300])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    args = ap.parse_args()

    env = load_env(args.env_file)
    tok = call(
        TOKEN_URL,
        {
            "app_id": env.get("FEISHU_APP_ID", ""),
            "app_secret": env.get("FEISHU_APP_SECRET", ""),
        },
    )
    if tok.get("code") != 0:
        print("token failed: code=%s msg=%s" % (tok.get("code"), tok.get("msg")))
        return 1

    res = call(INFO_URL, token=tok["tenant_access_token"])
    bot = (res.get("data") or res).get("bot") or {}
    if res.get("code") != 0 or not bot.get("open_id"):
        print("bot info failed: code=%s msg=%s" % (res.get("code"), res.get("msg")))
        return 1

    print("app_name=%s" % bot.get("app_name"))
    print("open_id=%s" % bot.get("open_id"))
    print("activate_status=%s" % bot.get("activate_status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
