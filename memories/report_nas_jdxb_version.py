#!/usr/bin/env python3
"""NAS 节点小宝版本核查结论，@ BOSS 发送。纯文本 + 半角引号。"""
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
    '<at user_id="%s"></at> NAS 端节点小宝查完了，结论先行：它已经是最新版本，没有可升的。\n\n'
    '一、证据\n'
    'NAS 现网容器镜像 ionewu/nblink:v4.2.3-821，但镜像 tag 不等于程序版本，里面真正的服务端程序 ownbsv 是 4.3.5，'
    '二进制构建日期 10 月 1 日。\n'
    '我把官方 Docker Hub 的最新镜像 ionewu/owjdxb:latest 拉下来拆开比对：内部版本同样 4.3.5，'
    '二进制构建日期 8 月 25 日。版本号一致，而 NAS 上这个构建更新。也就是说官方没有比 NAS 更高的服务端版本。\n\n'
    '二、容易误会的一点\n'
    'Docker Hub 上那个 latest 看着像新版，其实只是打包渠道不同，内核版本一样。服务端 4.3.5 落后客户端 '
    '4.5.2 到 4.5.3 是官方自己的发布节奏，实测兼容，今天隧道日志里有真实双向字节。\n\n'
    '三、我做了什么\n'
    '为了验证有没有自升级通道，重启了一次容器，约 40 秒，全员短暂掉线。重启后全量复测：Windows super、星期五、'
    '小豆三台的 16880 全部回 404 加 19 字节，SSH 登录星期五正常，peerid 仍是 B84CEAA15FDF8765OW，没有掉绑。\n'
    '备份：重启前已把 /owjdxb/ownbsv 与 /owjdxb/bin 备份到持久层 /data/store/OWData/owjdxb/ 下带时间戳目录。'
    '比对完的官方镜像已删除，NAS 上只留原镜像。\n\n'
    '四、下一步\n'
    'NAS 不动，也不用换镜像。等官方发布高于 4.3.5 的服务端版本再升，届时我再报你，会挑低峰窗口。'
    '客户端继续自动跟随，不用管。'
) % BOSS

T = tok()
body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + T}), timeout=20)
d = json.loads(r.read())
mid = d.get("data", {}).get("message_id")
ms = [m.get("id") for m in (d.get("data", {}).get("mentions") or [])]
print("code=", d.get("code"), "msg_id=", mid)
print("mentions=", ms)
print("AT_BOSS_OK=", BOSS in ms)
