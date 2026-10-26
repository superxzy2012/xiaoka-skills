#!/usr/bin/env python3
"""muse 独立凭据进展 + 公网暴露决策，@ BOSS。"""
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
    '<at user_id="%s"></at> muse 独立凭据这事，我推进到一半，有一个决策必须等你，先别让我半夜在公网开洞。\n\n'
    '已完成（内网侧）：\n'
    '1. 在 Gitea 给 muse 建了独立账号（id=11），只授权 anc/a2a-bus 一个仓、write 权限，'
    '跟 jarvis/xiaodou/小豆它们一样的模式。随机强密码已存 /opt/data/secrets/muse-gitea-creds.txt（600）。\n'
    '2. 但建号时一个参数把账号置成了"禁止登录"态，需要一次管理员 PATCH 解禁（命令我已备好，属于账号变更，审批刚才没通过，等你在线放行）。\n\n'
    '卡住的核心问题——双通物理上做不到零暴露：\n'
    'muse 在公网云端，Gitea 在你家内网，它平台又不让装组网客户端。它要直连内网正本，唯一办法是把 Gitea 暴露到公网。这等于在你家网络开个入口，我不擅自动。\n\n'
    '我给的方案排序：\n'
    'A 保持现在的 GitHub 中继（推荐，零新增风险）：每 5 分钟自动双向，实测已经完全能用，唯一代价是有最长 5 分钟延迟、且依赖我这台 NAS 在线。对 muse 这种非实时任务完全够。\n'
    'B Cloudflare Tunnel：最安全的公网暴露，不开放端口、走加密隧道、可随时吊销。但需要你的 Cloudflare 账号授权（域名/API token），这个我没有。\n'
    'C 路由器端口转发直暴 3000：需要你在路由器配，而且 Gitea 会裸奔在公网，我不建议。\n\n'
    '我的建议：先用 A（它已经在稳定跑），等你真的觉得 5 分钟延迟不可接受、或想要 muse 不依赖 NAS，我们再上 B。'
    '你醒了回我一个字母就行：A 维持现状 / B 配 Cloudflare（把账号给我）/ C 你自己开端口。'
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
