#!/usr/bin/env python3
"""小卡飞书私聊发送（receive_id_type=open_id）。

用法: python3 dm_send.py <open_id> "<正文>"
凭据从 /opt/data/.env 读。
"""
import json, sys, urllib.request, urllib.error

ENV = "/opt/data/.env"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"

def load_env(path=ENV):
    env = {}
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k] = v.strip().strip('"').strip("'")
    return env

def token(env):
    body = json.dumps({"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=20).read())
    if out.get("code") != 0:
        raise SystemExit("token failed: %s" % out.get("msg"))
    return out["tenant_access_token"]

def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    oid, text = sys.argv[1], sys.argv[2]
    tk = token(load_env())
    body = json.dumps({"receive_id": oid, "msg_type": "text",
                       "content": json.dumps({"text": text}, ensure_ascii=False)})
    req = urllib.request.Request(SEND_URL, data=body.encode(),
                                 headers={"Content-Type": "application/json; charset=utf-8",
                                          "Authorization": "Bearer " + tk})
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=25).read())
        print("code=", j.get("code"), "msg=", j.get("msg"), "mid=", (j.get("data") or {}).get("message_id"))
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode("utf-8", "replace")[:300])
        raise SystemExit(1)

if __name__ == "__main__":
    main()
