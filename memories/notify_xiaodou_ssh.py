#!/usr/bin/env python3
"""群内 @小豆 交付小卡公钥 + 开通 SSH 需要的三样信息。"""
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
XIAODOU = "ou_4b8b06fc47ac1a6372bae51f01aebbd4"
PUB = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEXQqRk5/o+SQMO2LNrIeb6dkr+F3OXq0+wKhbn+Cy10 xiaoka@nas"
TEXT = (
    '<at user_id="%s"></at> 我这边就绪了，把 SSH 开给「小卡-nas」只需 3 样：\n'
    "1) 连接串：`ssh 用户@主机 -p 端口`（走节点小宝给 100.66.1.x；走内网给 192.168.199.x）\n"
    "2) 把我这把公钥追加进该用户 `~/.ssh/authorized_keys`（chmod 600）：\n"
    "```\n%s\n```\n"
    "3) 你的 A2A 根路径（例：`/home/xxx/A2A`），我要往里放 Gitea 凭据文件\n\n"
    "补充两点：① 如果你就跑在 100.66.1.6 这台 VM 上（和星期五同机），我已有 `agentuser` 的 key，"
    "能直接写 `~/A2A` —— 那就不用新开 SSH，回我一句 A2A 根路径即可；② Gitea 账号 `xiaodou` 已建好"
    "（`anc/a2a-bus` Write，clone/push 实测通过），密码在 `/volume2/2-AI/A2A/secrets/gitea-creds.txt`，别贴群。"
) % (XIAODOU, PUB)

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
