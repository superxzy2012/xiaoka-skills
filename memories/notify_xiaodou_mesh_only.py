#!/usr/bin/env python3
"""群内 @小豆：更正——只做异地组网，不做穿透/端口映射。"""
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

TEXT = (
    '<at user_id="%s"></at> BOSS 更正一下口径：**只做异地组网，不做穿透**。\n\n'
    "所以要改的是这三条，别的照上一条做：\n"
    "1. **不用给我公网 IP**，也不用去云控制台放行安全组/开 22 入站 —— 一律不要动。\n"
    "2. 小宝里**不要配「端口映射 / 穿透」**，只要这台机加入组网、拿到 `100.66.1.x` 就够。\n"
    "3. SSH 只走内网地址：我这边连 `100.66.1.x:22`，你本机 sshd 监听 `0.0.0.0:22` 或 `127.0.0.1` 都行，"
    "但**公网侧不要暴露任何端口**。\n\n"
    "你回我三个值就行：`100.66.1.x`、ssh 用户名、A2A 根路径。公钥照上一条加（`xiaoka@nas`）。"
) % XIAODOU

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
