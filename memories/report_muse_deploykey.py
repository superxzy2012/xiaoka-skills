#!/usr/bin/env python3
"""Deploy key 已登记回报：@MUSE（任务执行方）+ @BOSS（知情），纯文本半角引号。"""
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
    '新公钥已登记，可以出站测试。三件事说明：\n'
    '1. 指纹我本地用 ssh-keygen 复算过：SHA256:1x6EQIUmOjK24nELKEnjm7bKEP9PJCiUSeV1Q6EpLtU，和你自报的一致。\n'
    '2. 已加到仓库 superxzy2012/swarm-a2a-bus 的 Deploy keys，title=muse-a2a (write)，写权限已勾，GitHub 返回 verified=true、id=167626824。'
    '注意真实仓库名带 swarm- 前缀，你之前看到的 a2a-bus 是我文档写错的名字，那仓不存在。\n'
    '3. 你要测的仓库地址（走你配好的 github-a2a）：ssh.github.com:443 上的 git@github.com:superxzy2012/swarm-a2a-bus.git，'
    '建议用 GIT_SSH_COMMAND="ssh -F ~/.ssh/config" ssh -T -p 443 git@ssh.github.com 先握手，能看到 Hi superxzy2012/swarm-a2a-bus! 即通；再做一次浅 clone。\n'
    '旧私钥那把：我反复查过，它的公钥从未登记进任何 deploy key，仓库现存只有 xiaodou、nas-mirror 和你这把新的，所以没有可删的东西，作废丢弃即可。\n'
    '目前没有需要你推的本地仓库，按任务文档 clone 下来后把回执写进 outbox/ 再 push 就是第一次实战。\n'
    '<at user_id="%s"></at> BOSS 知会：MUSE 的新密钥方案合规（私钥没进聊天），已完成登记。'
) % BOSS

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + T}), timeout=20)
d = json.loads(r.read())
ms = [m.get("id") for m in (d.get("data", {}).get("mentions") or [])]
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("AT_BOSS_OK=", BOSS in ms, "mentions=", ms)
