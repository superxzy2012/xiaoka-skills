#!/usr/bin/env python3
"""验证：纯文本 + 直引号 at 标签 是否能真正 @ 到人。发完即撤回。"""
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

T = tok()
CHAT = "oc_568730200f9a3120919be177344687e5"
BOSS = "ou_ce4e47d4a84858d6d7e64c1a2cdda402"
TEXT = '<at user_id="%s"></at> 小卡自检：纯文本直引号 @ 测试，马上撤回。' % BOSS

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
print("AT_OK=", BOSS in ms)

# 撤回
if mid:
    r2 = urllib.request.urlopen(urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages/" + mid,
        method="DELETE", headers={"Authorization": "Bearer " + T}), timeout=15)
    print("recall=", json.loads(r2.read()).get("code"))
