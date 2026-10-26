#!/usr/bin/env python3
"""只发一条 @ 星期五 的自检消息（纯文本、半角引号），用于端到端验证。"""
import json, urllib.request

ENV = {}
for line in open('/opt/data/.env'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        ENV[k.strip()] = v.strip().strip('"').strip("'")

def tok():
    body = json.dumps({"app_id": ENV["FEISHU_APP_ID"], "app_secret": ENV["FEISHU_APP_SECRET"]}).encode()
    r = urllib.request.urlopen(urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=body, headers={"Content-Type": "application/json"}), timeout=15)
    return json.loads(r.read())["tenant_access_token"]

CHAT = "oc_568730200f9a3120919be177344687e5"
FRIDAY = "ou_b172b28aa8416f7fca826bc151b9cbb8"
TEXT = '<at user_id="%s"></at> 模型链路刚修好，自检一下：只回一句「链路已恢复」加当前时间，不要展开。' % FRIDAY

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
req = urllib.request.Request("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
                             data=body, headers={"Content-Type": "application/json",
                                                 "Authorization": "Bearer " + T})
try:
    d = json.loads(urllib.request.urlopen(req, timeout=20).read())
    print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
    print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])
