#!/usr/bin/env python3
"""拉群里最近 15 条消息，找 星期五 发的内容里有没有报错字样。"""
import json, urllib.request, urllib.parse, time

ENV = {}
for line in open('/opt/data/.env'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        ENV[k.strip()] = v.strip().strip('"').strip("'")

body = json.dumps({"app_id": ENV["FEISHU_APP_ID"], "app_secret": ENV["FEISHU_APP_SECRET"]}).encode()
T = json.loads(urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=body, headers={"Content-Type": "application/json"}), timeout=15).read())["tenant_access_token"]

CHAT = "oc_568730200f9a3120919be177344687e5"
FRIDAY = "ou_b172b28aa8416f7fca826bc151b9cbb8"

def get(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"Authorization": "Bearer " + T}), timeout=20)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:300]}

q = urllib.parse.urlencode({"container_id_type": "chat", "container_id": CHAT,
                            "sort_type": "ByCreateTimeDesc", "page_size": 15})
d = get("https://open.feishu.cn/open-apis/im/v1/messages?" + q)
if d.get("error"):
    print("LIST_FAIL", d)
else:
    items = d.get("data", {}).get("items") or []
    print("count:", len(items))
    for it in items:
        sender = (it.get("sender") or {}).get("id")
        who = "星期五" if sender == FRIDAY else sender
        try:
            c = json.loads(it.get("body", {}).get("content") or "{}")
        except Exception:
            c = {}
        txt = (c.get("text") or c.get("content") or str(c))[:110].replace("\n", " ")
        ts = time.strftime("%H:%M:%S", time.localtime(int(it.get("create_time", "0")) / 1000))
        print(f"{ts} [{who}] {txt}")
