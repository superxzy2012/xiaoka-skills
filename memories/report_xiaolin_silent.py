#!/usr/bin/env python3
"""小林没回的原因判断，@ BOSS。"""
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
    '<at user_id="%s"></at> 我这边发了，@ 也确实生效了（飞书接口返回的 mentions 里有小林那个 id），但小林一直没回。'
    '我盯了 8 分钟的群消息事件，这段时间群里只有星期五在说话，小林一条都没冒头。\n\n'
    '最可能的原因是老毛病：Hermes 默认不响应 bot 发的消息。我这条是以机器人身份发的，它那边 allow_bots 没开的话，'
    '直接把我的消息丢掉，根本不会进它的大脑——小豆之前就是这个坑，改一行配置就好。\n\n'
    '你帮我做一个动作就能确认：在群里手动 @小林 说一句「回小卡一句」。如果它回了，说明是我被当成 bot 挡掉了；'
    '如果手动 @ 也不回，那它是没跑起来或者不在这个群里。\n\n'
    '要是它回了，让它把下面这句原话回给我，我就能接着走：\n'
    '「我是小林，跑在 muse 沙箱的 Ubuntu 上。主机名 X，Hermes 版本 X，技能有 X，能不能出网 X。」\n\n'
    '另外说一句：上一条我发错了内容，把你两个东西搞混了，我已经发更正道歉了。现在记清楚了——小林是你在 ubuntu 上装的 Hermes，'
    '网页上那个 muse 是另一个，以后运维指令不会再往网页 muse 发。'
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
