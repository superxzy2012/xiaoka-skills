#!/usr/bin/env python3
"""向管理群发降级结果报告，真实 @ BOSS。纯文本 + 半角引号。"""
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
    '<at user_id="%s"></at> 星期五降级结果，结论先行：4.3.5 切上去过，但被厂商自动升级抢回去了，'
    '而现在 4.5.3 下链路实测是通的，所以降级这件事的根因假设已被证伪。\n\n'
    '一、执行与回滚时间线\n'
    '21:22 星期五切到 4.3.5（ownbsvman 日志 ver=4.3.5，peerid 仍是 A6EACE9FF0406464OW，不用重绑）\n'
    '21:37 NAS 侧探针：16880 回 404/19 字节，:22 拿到 SSH banner，数据面通\n'
    '21:41 我调了一次 serv.sh，ownbsvman 启动时自动下载并覆盖回 4.5.3，二进制 md5 与备份完全一致，.version=4.5.3\n\n'
    '二、关键反证\n'
    '现在组合是 NAS 服务端 4.3.5 + 星期五客户端 4.5.3，NAS 隧道日志 21:47 记录 :22 mapping succ，'
    'sent 5947 recv 4305 字节；16880 mapping sent 668 recv 80。有真实双向字节，不是空连接。'
    '说明版本错配本身不致命，之前数据面全死是客户端会话死掉了，重启即恢复。\n\n'
    '三、请您定一个\n'
    'A 保持 4.5.3（我推荐）：链路已验证通，继续收官方修复，不用跟厂商的自动升级对着干。\n'
    'B 强行钉 4.3.5：需要停掉 ownbsvman 的版本同步，有断链风险，并且放弃后续修复。\n\n'
    '四、一个残留要您批\n'
    '我为了拦自动升级，在星期五的 /etc/hosts 加了 127.0.0.1 pcdntest2.ionewu.com，实测没拦住（它走别的通道）。'
    '这条撤销需要 sudo 改 /etc/hosts，刚才审批超时被拦了，您批一下我就清掉。\n\n'
    '4.3.5 安装包我已从 /tmp 挪到 ~/owjdxb/pkgs/ 保存，随时可再切。'
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
