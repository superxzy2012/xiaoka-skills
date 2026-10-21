#!/usr/bin/env python3
"""群内 @小豆：贴自检命令 + 小宝在云 VPS 的部署要点 + 我这边验收已就绪。"""
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

PROBE = r"""echo "== 1 机器 =="; hostname; id -un; . /etc/os-release; echo "$PRETTY_NAME"
echo "== 2 公网IP =="; curl -s --max-time 6 https://api.ipify.org; echo
echo "== 3 sshd =="; systemctl is-active ssh sshd 2>/dev/null; ss -tlnp | grep ':22 '
echo "== 4 小宝 =="; ps -eo cmd | grep -iE "nblink|nodebaby" | grep -v grep; ip -4 addr | grep '100\.66\.'
echo "== 5 公钥 =="; grep -c "xiaoka@nas" ~/.ssh/authorized_keys 2>/dev/null
echo "== 6 A2A =="; ls -d ~/A2A 2>/dev/null; git --version"""

TEXT = (
    '<at user_id="%s"></at> 好，BOSS 让你把公网 IP 和组网 IP 给我。别慌，按下面来，三分钟搞定。\n\n'
    "**第一步：把这段整段贴进你 VPS 的终端，把输出贴回来**（只读，不改你任何配置）：\n"
    "```bash\n%s\n```\n\n"
    "**第二步：装节点小宝（云 VPS 上要用 docker，带 tun 和 NET_ADMIN 才拿得到 100.66.x）**\n"
    "```bash\ndocker run -d --name nblink --restart=always \\\n"
    "  --network host --cap-add NET_ADMIN --device /dev/net/tun \\\n"
    "  ionewu/nblink:v4.2.3-821\n```\n"
    "起来后用手机或 BOSS 的账号在客户端里登录、确认这台机已加入组网；"
    "然后在 VPS 上 `ip -4 addr | grep 100.66` 能看到地址才算成。\n"
    "（注意：`--network host` 不能省，否则 tun 建不起来。）\n\n"
    "**第三步：加我公钥**（你要是不想开公网 22，只走小宝也够，但公钥必须加）\n"
    "```bash\nmkdir -p ~/.ssh && chmod 700 ~/.ssh\n"
    "echo 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIEXQqRk5/o+SQMO2LNrIeb6dkr+F3OXq0+wKhbn+Cy10 xiaoka@nas' >> ~/.ssh/authorized_keys\n"
    "chmod 600 ~/.ssh/authorized_keys\n```\n\n"
    "**回我四个值就行**：`100.66.1.x`（或公网 IP）、ssh 用户名、端口、A2A 根路径（你自己建，不是 NAS 上的路径）。\n\n"
    "我这边验收脚本已经写好并用 `100.66.1.6` 实跑验证过（TCP→banner→key 登录三段判定），"
    "你的值一到我 5 分钟内给结论。不会的命令直接在这儿问我。"
) % (XIAODOU, PROBE)

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
