#!/usr/bin/env python3
"""读管理群最近消息，找 friday 的发言与时间，判断其存活。"""
import json
import os
import urllib.parse
import urllib.request

ENV = "/opt/data/.env"


def load_env():
    d = {}
    for line in open(ENV, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip().strip('"').strip("'")
    return d


e = load_env()
APP_ID = e.get("FEISHU_APP_ID") or e.get("LARK_APP_ID")
APP_SECRET = e.get("FEISHU_APP_SECRET") or e.get("LARK_APP_SECRET")
BASE = "https://open.feishu.cn/open-apis"
CHAT = "oc_568730200f9a3120919be177344687e5"


def post(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def get(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    try:
        return json.loads(urllib.request.urlopen(req, timeout=15).read())
    except urllib.error.HTTPError as ex:
        print("HTTP", ex.code, ex.read().decode()[:400])
        raise


tok = post(BASE + "/auth/v3/tenant_access_token/internal",
           {"app_id": APP_ID, "app_secret": APP_SECRET})["tenant_access_token"]

q = urllib.parse.urlencode({"container_id_type": "chat", "container_id": CHAT,
                            "sort_type": "ByCreateTimeDesc", "page_size": 30})
r = get(BASE + "/im/v1/messages?" + q, tok)
print("code=", r.get("code"), r.get("msg"))
items = (r.get("data") or {}).get("items") or []
print("取到", len(items), "条")
for m in items:
    sender = m.get("sender", {})
    body = (m.get("body") or {}).get("content", "")
    try:
        txt = json.loads(body).get("text", "")
    except Exception:
        txt = body
    txt = txt.replace("\n", " ")[:90]
    import datetime
    ts = int(m.get("create_time", 0)) / 1000
    t = datetime.datetime.fromtimestamp(ts).strftime("%m-%d %H:%M:%S")
    print(f"{t} | {sender.get('sender_type')}:{sender.get('id','')[:14]} | {txt}")
