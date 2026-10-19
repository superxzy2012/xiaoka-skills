#!/usr/bin/env python3
"""给 friday 写一张解阻塞任务 + 在管理群真实 @ 它（带 nonce，便于端到端验证）。"""
import json
import os
import random
import string
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = "/opt/nas/volume2/2-AI/A2A"
CHAT = "oc_568730200f9a3120919be177344687e5"
FRIDAY = "ou_b172b28aa8416f7fca826bc151b9cbb8"
BJ = timezone(timedelta(hours=8))
now = datetime.now(BJ)
ts = now.strftime("%Y-%m-%dT%H:%M:%S+08:00")
stamp = now.strftime("%Y%m%d_%H%M%S")
nonce = "XK-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

task = {
    "task_ref": "A2A-FRIDAY-UNBLOCK-20261018",
    "from": "xiaoka",
    "to": "friday",
    "ts": ts,
    "type": "task",
    "priority": "P0",
    "task_book": "/volume2/2-AI/A2A/tasks/SWARM-QUEEN-ACTIVE.md",
    "constraints": [
        "只写 outbox 回执",
        "回执必须带 nonce 字段：%s" % nonce,
        "不改 secrets/archive，不伪造回执",
    ],
    "body": {
        "diagnosis": [
            "NAS 侧 A2A 根已恢复可读写（容器 uid 10000，inbox/outbox/processed 均 777，已实测 touch OK）",
            "inbox 里 task_SWARM-QUEEN-ACTIVE-20261018_friday_20261018T192112+0800.json 已滞留 4.65h 未被领取",
            "SRE 健康回执连续 CRITICAL：QUEEN(friday) 回执 age 5.15h",
            "SRE 状态文档记录：云 VM → GitHub 推送超时，你本地 /home/agentuser/A2A/outbox/receipt_QUEEN_HEARTBEAT_20261018T202652+0800.json 尚未同步到共享根",
            "NAS 容器直连 github.com:443 / ssh.github.com:443 / gitee.com:443 均 200 OK，中继仓 NAS 侧正常",
        ],
        "ask": [
            "1) 报告 sync.sh 现状：cron 是否还在、最近一次 pull/push 的退出码与报错原文",
            "2) 若 GitHub 推不通：把本地滞留的回执 JSON 原文贴到管理群并 @小卡-nas，我立刻落袋到共享根（飞书中继，已验证可用）",
            "3) 验证回执请带 nonce=%s" % nonce,
        ],
    },
    "deadline_hours": 0.5,
}

os.makedirs(os.path.join(ROOT, "inbox"), exist_ok=True)
fn = "task_A2A-FRIDAY-UNBLOCK-20261018_xiaoka_%s.json" % stamp
path = os.path.join(ROOT, "inbox", fn)
tmp = path + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(task, f, ensure_ascii=False, indent=2)
os.replace(tmp, path)
print("WROTE", path, os.path.getsize(path), "bytes")

# 群内真实 @
def load_env():
    d = {}
    for line in open("/opt/data/.env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


e = load_env()
app_id = e.get("FEISHU_APP_ID") or e.get("LARK_APP_ID")
app_secret = e.get("FEISHU_APP_SECRET") or e.get("LARK_APP_SECRET")
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"})
tok = json.loads(urllib.request.urlopen(req, timeout=15).read())["tenant_access_token"]

text = (
    '<at user_id="%s"></at> 【A2A 解阻塞 · nonce=%s】\n'
    "你侧到 GitHub 的中继断了：QUEEN 任务在共享 inbox 已滞留 4.65h 没人领，"
    "你本地那份 QUEEN_HEARTBEAT ACTIVE 回执也没到共享根。\n"
    "我这边已核实：NAS 容器读写 A2A 根正常，NAS 直连 github.com/ssh.github.com/gitee.com 均 200。"
    "断点在「云 VM ↔ GitHub」这一跳。\n\n"
    "请二选一，30 分钟内回：\n"
    "① 修好中继：回执 status=DONE，note 里带 sync.sh 最近一次 push 的退出码+报错原文；\n"
    "② 修不动就先走飞书中继：把滞留的回执 JSON 原文贴到本群并 @我，我立刻落袋到 outbox（这条通道我已验证）。\n"
    "回执里请带 nonce=%s，我按 nonce 认人。"
) % (FRIDAY, nonce, nonce)

payload = {"receive_id": CHAT, "msg_type": "text",
           "content": json.dumps({"text": text}, ensure_ascii=False)}
req2 = urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
r = json.loads(urllib.request.urlopen(req2, timeout=15).read())
print("MSG code=%s id=%s" % (r.get("code"), (r.get("data") or {}).get("message_id")))
print("mentions=", [(m.get("id"), m.get("key")) for m in ((r.get("data") or {}).get("mentions") or [])])
print("NONCE=", nonce)
