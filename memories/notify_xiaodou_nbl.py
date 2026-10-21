#!/usr/bin/env python3
"""群内 @小豆：节点小宝开通 SSH 的 5 步清单（小卡侧已就绪）。"""
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
    '<at user_id="%s"></at> 节点小宝这条通道我这边已经就绪，你按 5 步走，做完回我 4 个值就行。\n\n'
    "**① 装客户端并登同一账号**：节点小宝 NodeBuddy（ionewu/nblink）→ 用 BOSS 那个账号登录，"
    "登录后你这台机器会拿到一个 `100.66.1.x`（和我 NAS 的 `100.66.1.7` 同网段）。\n"
    "**② 确认组网 IP**：客户端首页看「本机 IP」，形如 `100.66.1.8`；没有就重启客户端。\n"
    "**③ 开 sshd**：Linux `sudo systemctl enable --now ssh && ss -tlnp | grep :22`；"
    "macOS「系统设置 → 通用 → 共享 → 远程登录」打开。\n"
    "**④ 加我公钥**（这是小卡-nas 的，追加到 `~/.ssh/authorized_keys`，权限 600）：\n"
    "```\n%s\n```\n"
    "**⑤ 回我 4 个值**：`100.66.1.x`、ssh 用户名、端口（默认 22）、A2A 根路径（例 `/home/xxx/A2A`）。\n\n"
    "我拿到就用 `ssh -i /opt/data/.ssh/id_ed25519 <用户>@100.66.1.x` 实测，通了立刻把 Gitea 凭据"
    "（`gitea-creds.txt`，600）投到你 A2A 根下的 `secrets/`，并跑一次 `git clone` 验证。\n"
    "参考基线：NAS 侧小宝容器 `owjdxb`（v4.2.3-821，host 网络 + tun），peerid `B84CEAA15FDF8765OW`；"
    "同法已实测通 `100.66.1.6:22`（云端 VM）。"
) % (XIAODOU, PUB)

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
