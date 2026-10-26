#!/usr/bin/env python3
"""@ 星期五 做一次端到端模型验证：发一条纯文本消息，然后轮询群消息看它是否回复。"""
import json, time, urllib.request, urllib.parse

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

TEXT = '<at user_id="%s"></at> 模型链路刚修好，帮我做一次自检：请只回一句「链路已恢复」加当前时间，不要展开。' % FRIDAY

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + T}), timeout=20)
d = json.loads(r.read())
mid = d.get("data", {}).get("message_id")
print("sent:", d.get("code"), mid)

# 轮询 120 秒，看是否有非本 app 的回复
for i in range(24):
    time.sleep(5)
    q = urllib.parse.urlencode({"container_id_type": "chat", "container_id": CHAT,
                                "sort_type": "ByCreateTimeDesc", "page_size": 8})
    r = urllib.request.urlopen(urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/messages?" + q,
        headers={"Authorization": "Bearer " + T}), timeout=20)
    items = json.loads(r.read()).get("data", {}).get("items") or []
    for it in items:
        if it.get("message_id") == mid:
            continue
        sender = (it.get("sender") or {}).get("id")
        if sender == FRIDAY:
            c = json.loads(it.get("body", {}).get("content") or "{}")
            print("REPLY after %ds: %s" % ((i + 1) * 5, str(c)[:200]))
            raise SystemExit(0)
print("NO_REPLY_IN_120S")
