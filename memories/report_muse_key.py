#!/usr/bin/env python3
"""MUSE 报错定性 + 两条解法，@ BOSS。"""
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
    '<at user_id="%s"></at> 这条不是故障，是 MUSE 在拦你。它拒收私钥是对的：私钥一旦贴进聊天记录就等于废了，'
    '任何拿到记录的人都能拿去推你的仓库。所以它每收到一次私钥，就会回你一次这段话，你看着难受的正是它尽责。\n\n'
    '我查了 GitHub 那边的实况：\n'
    '1. 那把 muse-a2a-bus 私钥从来没被登记成 deploy key，仓库里只有 xiaodou 和 nas-mirror 两把。所以不用去撤销，直接当废纸丢掉就行，没人能用它。\n'
    '2. 更要紧的是，我发现自己昨天写的接入文档把仓库名写错了：写成了 superxzy2012/a2a-bus，真实仓库是 superxzy2012/swarm-a2a-bus。'
    'MUSE 照着文档去拉，只会得到 Repository not found，然后一遍遍重试、一遍遍报错。这个已经改好了。\n\n'
    '正确的做法本来就不该用私钥。两条路你选一条：\n'
    'A 零配置，今天就能通：让 MUSE 把回执直接发到群里，我替它提交进仓库。它不需要任何密钥、任何权限，我这边有现成的推送凭据。缺点是我得在线。\n'
    'B 正规通道，它自己推：你在 GitHub 生成一个 fine-grained PAT，只给 swarm-a2a-bus 这一仓、只给 Contents 读写、90 天，然后私聊发给 MUSE。'
    '步骤我写在 A2A/tasks/MUSE-GIT-ONBOARD.md 第 1 节，照着点就行，两分钟。之后它自己 clone、自己 push，不用我。\n\n'
    '我的建议：先走 A 让链路今天跑通，B 你有空再补。你回「A」或「B」，或者两个都要。'
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
