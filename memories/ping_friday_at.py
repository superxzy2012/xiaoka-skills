#!/usr/bin/env python3
"""给星期五发真实 @ 的 ping，验证 mentions 命中。纯文本 + 半角引号。"""
import json, urllib.request, sys

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
TEXT = ('<at user_id="%s"></at> ping。小卡在群里发的这条是真实 @ 你的验证消息，'
        '收到请回一个字符即可（比如 1）。之前几条没 @ 上是我的错，已修。') % FRIDAY

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + T}), timeout=20)
d = json.loads(r.read())
mid = d.get("data", {}).get("message_id")
ms = [m.get("id") for m in (d.get("data", {}).get("mentions") or [])]
print("code=", d.get("code"), "msg_id=", mid)
print("mentions=", ms)
print("AT_FRIDAY_OK=", FRIDAY in ms)
