#!/usr/bin/env python3
"""写 A2A 任务：XIAODOU-GOVERNANCE-20261021（星期五治理小豆，小卡协助技术侧）"""
import json, secrets, subprocess, datetime

nonce = "XK-XDGOV-" + secrets.token_hex(3).upper()
task = {
    "task_id": "XIAODOU-GOVERNANCE-20261021",
    "from": "xiaoka",
    "to": "friday",
    "priority": "P1",
    "nonce": nonce,
    "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+0000"),
    "title": "BOSS 定：星期五治理小豆（群监控/@必回/教调试），小卡协助技术侧",
    "body": (
        "BOSS 2026-10-21 指派：由你（星期五）对小豆进行治理——群消息要监控、@小豆的要回复、链路不通的要教会调试；小卡协助技术侧。\n"
        "\n【分工】\n"
        "· 星期五：群内 @小豆 的应答、催办、答疑、进度看板；判断“不会”还是“坏了”。\n"
        "· 小卡：节点小宝组网与 SSH 验收、Gitea 凭据投递、权限变更、链路诊断脚本。\n"
        "\n【硬口径（BOSS 定，勿改）】\n"
        "· 小豆接入只做「节点小宝异地组网」，**不做穿透/端口映射**；不开公网端口、不动云安全组。\n"
        "· 小豆 = 云端 VPS 全新实例（2026-10-21 起），与旧 Mac 端无关；也与你这台 VM(100.66.1.6) 是不同机器、不同云，路径/凭据不可互套。\n"
        "\n【当前状态】\n"
        "· Gitea：账号 xiaodou 已建（uid=8，非 admin，anc/a2a-bus Write），clone + push dry-run 实测通过；密码在 A2A/secrets/gitea-creds.txt（600）。\n"
        "· SSH：等小豆回三个值——100.66.1.x / ssh 用户名 / A2A 根路径。\n"
        "\n【工具（已放共享 A2A/tools/，可 rsync 到你侧）】\n"
        "· xiaodou_vps_probe.sh —— 让小豆在自己 VPS 上跑，只读自检，输出贴群（机器/公网IP/sshd/小宝/公钥/A2A）。\n"
        "· xiaodou_link_check.py <ip> [user] [port] —— 三段判定：TCP → SSH banner → key 登录；已用 100.66.1.6 实跑验证通过。\n"
        "\n【链路不通时的六步诊断（按序，别跳）】\n"
        "1. 他本机 `ip -4 addr | grep 100.66` 有没有组网地址（没有=小宝没连上/tun 没建，常见是 docker 漏 --network host --cap-add NET_ADMIN --device /dev/net/tun）。\n"
        "2. 小卡侧 `xiaodou_link_check.py`：TCP 不通 → 小宝没在同一网络/账号。\n"
        "3. 注意：relay 模式 ICMP 不通是正常的，只认 TCP。\n"
        "4. TCP 通但 banner 空 → 中转接上了但目标端口没监听（sshd 没起）。\n"
        "5. banner 有 OpenSSH 但 key 登录失败 → authorized_keys 没写/权限不对（.ssh 700、authorized_keys 600）。\n"
        "6. 全都对但连不上 → 检查是否误配了端口映射（BOSS 明确不要穿透）。\n"
        "\n【治理节拍（建议）】\n"
        "· 群内 @小豆 30 分钟无回 → 你追问一次，给具体命令而不是“在吗”。\n"
        "· 2 小时无回 → 记 A2A 任务并 @小卡，我这边从网络侧查。\n"
        "· 每次小豆卡住，把“他缺哪一步/该跑哪条命令”写进 A2A/agents/xiaodou.md，别只留在群聊。\n"
        "\n回执请带 nonce。"
    ),
    "expect": "receipt",
}

path = f"/opt/data/cache/scratch/task_XIAODOU-GOVERNANCE-20261021_xiaoka_{datetime.datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
with open(path, "w") as f:
    json.dump(task, f, ensure_ascii=False, indent=2)
print("local:", path)
print("nonce:", nonce)

remote = "/volume2/2-AI/A2A/inbox/" + path.split("/")[-1]
r = subprocess.run(
    ["ssh", "-i", "/opt/data/.ssh/id_ed25519", "-o", "StrictHostKeyChecking=no",
     "-o", "UserKnownHostsFile=/dev/null", "DY@192.168.199.2",
     f"cat > '{remote}' && chmod 644 '{remote}' && ls -l '{remote}'"],
    stdin=open(path, "rb"), capture_output=True, text=True, timeout=60)
print("rc=", r.returncode, r.stdout.strip()[-200:], r.stderr.strip()[-150:])
