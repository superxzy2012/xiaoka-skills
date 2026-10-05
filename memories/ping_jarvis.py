#!/usr/bin/env python3
"""小卡 -> 管理群 @贾维斯-XF 握手。

用法: python3 ping_jarvis.py <chat_id> <open_id> "<正文>"
凭据全部从 /opt/data/.env 读，不落任何 token 字面量。
API 响应里的 mentions 字段会告诉我们 @ 是否解析成功（open_id 是应用维度的）。
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
    body = json.dumps(
        {"app_id": env["FEISHU_APP_ID"], "app_secret": env["FEISHU_APP_SECRET"]}
    ).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=body, headers={"Content-Type": "application/json"}
    )
    out = json.loads(urllib.request.urlopen(req, timeout=20).read())
    if out.get("code") != 0:
        raise SystemExit("token failed: %s" % out.get("msg"))
    return out["tenant_access_token"]


def send(token, chat_id, text):
    content = json.dumps({"text": text}, ensure_ascii=False)
    body = json.dumps({"receive_id": chat_id, "msg_type": "text", "content": content})
    req = urllib.request.Request(
        SEND_URL,
        data=body.encode(),
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": "Bearer " + token,
        },
    )
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def main():
    chat_id, open_id, text = sys.argv[1], sys.argv[2], sys.argv[3]
    token = tenant_token(load_env())
    # 真正的 @ 必须用 <at user_id="ou_xxx"></at> 标签；纯文本 "@名字" 只是字面量。
    body = '<at user_id="%s"></at> %s' % (open_id, text)
    res = send(token, chat_id, body)
    print("code=", res.get("code"), "msg=", res.get("msg"))
    data = res.get("data") or {}
    print("message_id=", data.get("message_id"))
    mentions = data.get("mentions") or []
    if mentions:
        for m in mentions:
            print("mention ok ->", m.get("name"), m.get("id"))
    else:
        print("mentions=[]  <-- @ 未解析：open_id 跨应用不一致，需用「发送方视角」的 id")


if __name__ == "__main__":
    main()