#!/usr/bin/env python3
"""防火墙自愈服务安装完成回报，@ BOSS。"""
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
    '<at user_id="%s"></at> 装好了，两层保险。\n'
    'nblink-fw.service：开机自动补规则，排在 tailscaled 之后跑。\n'
    'nblink-fw-check.timer：每 15 分钟检查一次，规则没了就补。加这个是因为 tailscaled 自己更新时会重启并重建它的防火墙链，光靠开机那一次会漏。\n'
    '自愈实测：我故意把规则删了，然后手动触发检查服务，规则自动回来了，OmniRoute 0.05 秒回 401。下次自动检查在 23:36。\n'
    '两个 unit 都已 enabled + active，重启机器不会丢。'
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
