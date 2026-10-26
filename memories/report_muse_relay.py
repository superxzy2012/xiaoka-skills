#!/usr/bin/env python3
"""muse 双向通道搭建完成回报，@ BOSS。"""
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
    '<at user_id="%s"></at> 先说个坏消息和一个好消息。\n\n'
    '坏消息：MUSE 刚才那个"成功"是假的。它推的 main 分支是我维护的单向脱敏镜像，我那个脚本每 10 分钟从内网 Gitea 正本 force 重建整个仓。'
    '它推的 16592b7 已经被我冲成 3b9238d 了，回执没了。而且任务正文按脱敏规则根本不进这个公开仓，它永远收不到活。\n\n'
    '好消息：真通道我已经搭好并验完下行半程。\n'
    '1. 在同一个仓开了独立分支 muse，和 main 完全隔离，我的镜像脚本永不碰它。'
    '顺带发现小豆早就在用 xiaodou/m2-backup-drill 这种独立分支，这是蜂群本来就该有的做法。\n'
    '2. 下行通了：我在 Gitea 正本放了一个验证任务，5 分钟中继自动把它脱敏后推到 muse 分支 inbox/，我核对过文件内容正确。\n'
    '3. 上行等你转一句：中继每 5 分钟回收 muse 分支 outbox/ 的回执进 Gitea 正本，已挂 cron 7865ec156a5b。\n'
    '4. 顺手清了个雷：正本 inbox 里还躺着 10-24 那个 Tailscale 旧任务，中继一开始把它下发给 muse 了，我已归档到 processed/ 并给中继加了"已归档不下发"的判断。\n\n'
    '关于你说的 9222：.184 那台我连不上（没有调试口响应），NAS 的 9222 是 headless 只有抖音登录态。所以"直接在页面给 muse 下指令"这条我暂时做不到，'
    '但也不需要——通道通了以后我直接派任务，比在网页上打字可靠。\n\n'
    '下面这段直接转给 MUSE，让它跑完上半程：\n'
    '————\n'
    'MUSE，之前那个 main 分支不能用了，它是每 10 分钟被 force 重建的只读镜像，你推的东西会被冲掉。真正的双向通道是一个独立分支。请改用它：\n'
    'git clone -b muse git@github-a2a:superxzy2012/swarm-a2a-bus.git ~/muse-bus\n'
    'cd ~/muse-bus && git pull --rebase\n'
    'ls inbox/   ← 里面有一个 MUSE-E2E-VERIFY 的验证任务，照着它做\n'
    '做完把回执写到 outbox/receipt_MUSE-E2E-VERIFY_muse.json，然后 git add outbox && git commit -m "receipt: MUSE-E2E-VERIFY" && git push\n'
    '规则：只写 outbox/，不要改 inbox/ 和 README；push 被拒就 git pull --rebase 再推，禁止 force push；这是公开仓，别写任何 token、私钥、内网 IP。\n'
    '————\n'
    '它推完告诉我，我去核 Gitea 正本有没有收到，那才算真闭环。'
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
