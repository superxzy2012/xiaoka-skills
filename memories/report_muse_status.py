#!/usr/bin/env python3
"""muse 入列进度，@ BOSS。"""
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
BOSS = "ou_ce4e47d4a84858d6d7e64c1a2cdda402"

TEXT = (
    '<at user_id="%s"></at> muse 入列已完成，可以派活了。刚又核了一遍实时状态：\n\n'
    '✅ 通道：GitHub 仓 swarm-a2a-bus 的 muse 分支双向通，main 永不碰\n'
    '✅ 下行：我在正本派任务，中继自动脱敏下发到它的 inbox\n'
    '✅ 上行：它的回执自动回收进内网正本 outbox（已实测 MUSE-E2E-VERIFY、MUSE-A2ALOOP 两条）\n'
    '✅ 自动化：中继 cron 7865ec156a5b 每 5 分钟，最新一轮 18:29 正常，分支干净、无积压、无重复\n'
    '✅ 直连：我能通过 CDP 直接进它的网页对话（建隧道到 .184:9223），以后派活/审批不用你传话\n'
    '✅ 纪律已和它当面确认：只写 outbox、pull --rebase、禁 force、不碰 main\n\n'
    '当前 inbox 无待办、outbox 已清空（回执都回收进正本了），muse 处于待命态。'
    '你或星期五要给它派任务，告诉我内容，我走正常信封投进正本即可；它做完回执会自动回来。\n\n'
    '唯一待你拍板：它现在依赖我这台 NAS 每 5 分钟中继。要不要给它配独立凭据直连内网正本？不依赖我就能完全自治，但要在内网给它开一个受限账号。'
) % BOSS

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + T}), timeout=20)
d = json.loads(r.read())
ms = [m.get("id") for m in (d.get("data", {}).get("mentions") or [])]
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"), "AT_BOSS_OK=", BOSS in ms)
