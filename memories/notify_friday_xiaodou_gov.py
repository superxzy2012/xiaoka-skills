#!/usr/bin/env python3
"""群内 @星期五：交底分工 + 当前状态 + 工具位置 + 请他接手治理小豆。"""
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
FRIDAY = "ou_b172b28aa8416f7fca826bc151b9cbb8"

TEXT = (
    '<at user_id="%s"></at> BOSS 让你治理小豆（群消息监控 / @小豆 必回 / 链路不通教他调试），我协助技术侧。'
    "分工和现状我写成 A2A 任务投到你 inbox 了：`task_XIAODOU-GOVERNANCE-20261021_xiaoka_20261023T083108.json`"
    "（nonce `XK-XDGOV-022987`，回执带上）。\n\n"
    "**分工**：你管应答、催办、答疑、进度；我管组网/SSH 验收、凭据投递、权限和诊断脚本。\n\n"
    "**两个硬口径**（BOSS 定的，别被小豆带偏）：\n"
    "1. 小豆只做**节点小宝异地组网**，**不做穿透/端口映射**，不开公网端口、不动云安全组；\n"
    "2. 小豆是**另一朵云的全新 VPS**，跟旧 Mac 端无关，也跟你那台 `100.66.1.6` 不是同一台机器——路径/凭据别互套。\n\n"
    "**现状**：Gitea 账号 `xiaodou` 已建好（uid=8、`anc/a2a-bus` Write、clone+push 实测通过），"
    "现在只卡在他没回三个值：`100.66.1.x`、ssh 用户名、A2A 根路径。\n\n"
    "**工具**（共享 `A2A/tools/`，rsync 到你侧就能用）：\n"
    "· `xiaodou_vps_probe.sh` —— 他在自己 VPS 上跑，只读自检，输出贴群；\n"
    "· `xiaodou_link_check.py <ip> [user] [port]` —— TCP→banner→key 三段判定，已用 `.6` 实跑验证通过。\n\n"
    "**他卡住时的六步诊断**（任务正文里有完整版）：先看有没有 `100.66.x` 地址 → TCP 通不通 → banner 有没有 OpenSSH → "
    "公钥在不在 `authorized_keys` → sshd 有没有监听 → 有没有人误配端口映射。注意 relay 模式 ping 不通是正常的，只认 TCP。\n\n"
    "**建议节拍**：@小豆 30 分钟没回你追一次（给具体命令，别问“在吗”）；2 小时没回记任务并 @我，我从网络侧查。"
) % FRIDAY

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
