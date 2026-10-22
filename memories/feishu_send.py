#!/usr/bin/env python3
"""小卡通用飞书发消息（纯 API，无浏览器）。

用法:
  python3 feishu_send.py <chat_id> "<正文>"            # 不 @ 人
  python3 feishu_send.py <chat_id> "<正文>" --at ou_xx  # 开头 @ 某人（可多次）

凭据从 /opt/data/.env 读，绝不写 token 字面量。
发送后打印 API 返回的 mentions，用来确认 @ 是否真的解析（open_id 是应用维度的）。
"""
import json
import sys
import urllib.request

ENV = "/opt/data/.env"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"


def load_env(path=ENV):
    env = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v.strip().strip('"').strip("'")
    return env


def tenant_token(env):
    body = json.dumps({"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={"Content-Type": "application/json"})
    out = json.loads(urllib.request.urlopen(req, timeout=20).read())
    if out.get("code") != 0:
        raise SystemExit("token failed: %s" % out.get("msg"))
    return out["tenant_access_token"]


def send(tk, chat_id, text):
    content = json.dumps({"text": text}, ensure_ascii=False)
    body = json.dumps({"receive_id": chat_id, "msg_type": "text", "content": content})
    req = urllib.request.Request(
        SEND_URL,
        data=body.encode(),
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": "Bearer " + tk},
    )
    try:
        return json.loads(urllib.request.urlopen(req, timeout=25).read())
    except urllib.error.HTTPError as e:
        print("HTTP %s body: %s" % (e.code, e.read().decode("utf-8", "replace")[:400]))
        raise SystemExit(1)


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        raise SystemExit(__doc__)
    chat_id, text = args[0], args[1]
    ats = [args[i + 1] for i, a in enumerate(args) if a == "--at"]
    if ats:
        text = " ".join('<at user_id="%s"></at>' % o for o in ats) + " " + text
    res = send(tenant_token(load_env()), chat_id, text)
    print("code=", res.get("code"), "msg=", res.get("msg"))
    data = res.get("data") or {}
    print("message_id=", data.get("message_id"))
    mentions = data.get("mentions") or []
    if mentions:
        for m in mentions:
            print("mention ok ->", m.get("name"), m.get("id"))
    else:
        print("mentions=[]  <-- @ 未解析（open_id 跨应用不一致）")


if __name__ == "__main__":
    main()
