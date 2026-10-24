#!/usr/bin/env python3
"""Settle "is this open_id valid in MY app's view?" with one API call.

Sends a single group message that @-mentions every candidate id, then prints the id the API
echoed back for each mention. An echo equal to your known local id means that candidate
resolved; a candidate with no mention entry did not resolve.

  python3 feishu_dual_id_probe.py --chat oc_xxx --id ou_selfreported --id ou_observed
  python3 feishu_dual_id_probe.py --chat oc_xxx --id ou_xxx --env-file ~/.hermes/.env

Exit 0 = every candidate resolved, 3 = some did not, 1 = API/credential error.
Credentials are read from the env file and never printed.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

DEFAULT_ENV = "/opt/data/.env"


def load_env(path):
    if not os.path.exists(path):
        sys.exit(f"env file not found: {path}")
    env = {}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def tenant_token(env):
    body = json.dumps({"app_id": env["FEISHU_APP_ID"],
                       "app_secret": env["FEISHU_APP_SECRET"]}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=body, headers={"Content-Type": "application/json"})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=20).read())
    except Exception as exc:  # noqa: BLE001 - report the type only, never the payload
        sys.exit(f"token request failed: {type(exc).__name__}")
    if j.get("code"):
        sys.exit(f"token error code={j.get('code')} msg={j.get('msg')}")
    return j["tenant_access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chat", required=True, help="group chat_id (oc_...)")
    ap.add_argument("--id", dest="ids", action="append", required=True,
                    help="candidate open_id; repeat for each")
    ap.add_argument("--text", default="【@ 解析探针】用于确认哪些 open_id 能解析，可忽略。")
    ap.add_argument("--env-file", default=DEFAULT_ENV)
    args = ap.parse_args()

    tags = "".join(f'<at user_id="{i}"></at>' for i in args.ids)
    payload = json.dumps({
        "receive_id": args.chat,
        "msg_type": "text",
        "content": json.dumps({"text": tags + " " + args.text}, ensure_ascii=False),
    }).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8",
                 "Authorization": "Bearer " + tenant_token(load_env(args.env_file))})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=25).read())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code} {exc.read().decode('utf-8', 'replace')[:300]}")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        print(f"send failed: {type(exc).__name__}")
        sys.exit(1)

    data = j.get("data") or {}
    mentions = data.get("mentions") or []
    print(f"code={j.get('code')} msg={j.get('msg')} message_id={data.get('message_id')}")
    print(f"candidates={len(args.ids)} resolved={len(mentions)}")
    echoed = {m.get("id") for m in mentions}
    for cid in args.ids:
        print(f"  {cid} -> {'RESOLVED' if cid in echoed else 'no mention'}")
    for n, m in enumerate(mentions):
        print(f"  mention[{n}] id={m.get('id')} name={m.get('name')!r} key={m.get('key')}")
    sys.exit(0 if len(mentions) >= len(args.ids) else 3)


if __name__ == "__main__":
    main()
