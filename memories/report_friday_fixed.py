#!/usr/bin/env python3
"""星期五模型报错修复结果，@ BOSS 发送。"""
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
    '<at user_id="%s"></at> 星期五修好了，报错不是模型本身的问题，是两个毛病叠在一起。\n\n'
    '一、真正的病根：Tailscale 把节点小宝的回包全丢了\n'
    '星期五那台装了 Tailscale，它的防火墙规则写着「凡是 100.64.0.0/10 段、又不是从 tailscale0 进来的包，一律丢弃」。'
    '节点小宝用的 100.66.1.0/24 正好落在这个段里，所以星期五发出去的请求包能走，回来的应答包全被防火墙丢掉。\n'
    '这也解释了为什么现象很怪：我能 SSH 进星期五，因为它入站走的是本地 127.0.0.1 映射，不经过隧道；'
    '但它自己访问 NAS 上的任何服务都超时。抓包看得清清楚楚：请求发出去、对端回了 SYN-ACK、本机却一直重发请求。\n'
    '修复就一行防火墙规则，让 NodeBabyLink 网卡进来的包跳过这条丢弃规则。加完立刻见效：OmniRoute 0.5 秒回 401，Gitea 0.13 秒回 200。\n'
    '顺带说明：我之前试的降版本是白忙，4.3.5 和 4.5.3 表现一模一样，跟版本无关。现在已把客户端恢复成厂商最新的 4.5.3。\n\n'
    '二、第二个毛病：火山方舟的额度用光了\n'
    '星期五主模型是 ark-coding，直测返回 429，原文是「5 小时用量配额已超」，要等到今晚 23:50 才恢复。'
    '它一旦 429 就往下切备用，而备用全走 OmniRoute，正好撞上第一个毛病，于是五次重试全挂，就成了你截图那样。\n\n'
    '三、我做的改动\n'
    '1. 加防火墙放行规则（已生效，但重启后会失效，需要你批准我装一个开机自动补规则的 systemd 服务，刚才那条审批超时没跑成）。\n'
    '2. 星期五主模型从 ark-coding 切成 OmniRoute 的 deepseek-v4.1-flash，备用顺序改成 free-pool、assistant、最后才 ark。这样不再天天吃 429。\n'
    '3. 重启了星期五的网关，实测新配置已加载，日志显示 Model context warmed: a2a/deepseek-v4.1-flash。\n\n'
    '四、验证结果\n'
    '我在群里 @ 它做自检，41 秒回了 35 个字，链路通了。你刚应该也看到它那条回复。\n\n'
    '还剩一件事等你点头：防火墙规则重启会丢，要不要我装那个开机自补的 systemd 服务？你回一句「装」我就上。'
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
print("AT_BOSS_OK=", BOSS in ms)
