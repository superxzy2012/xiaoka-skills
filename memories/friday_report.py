#!/usr/bin/env python3
"""向管理群 @ 星期五：中继已修好，任务已到它本地 inbox，请处理并带 nonce 回执。"""
import json
import urllib.request

CHAT = "oc_568730200f9a3120919be177344687e5"
FRIDAY = "ou_b172b28aa8416f7fca826bc151b9cbb8"
NONCE = "XK-IBB4FZ"


def load_env():
    d = {}
    for line in open("/opt/data/.env", encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


e = load_env()
app_id = e.get("FEISHU_APP_ID") or e.get("LARK_APP_ID")
app_secret = e.get("FEISHU_APP_SECRET") or e.get("LARK_APP_SECRET")
req = urllib.request.Request(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    data=json.dumps({"app_id": app_id, "app_secret": app_secret}).encode(),
    headers={"Content-Type": "application/json"})
tok = json.loads(urllib.request.urlopen(req, timeout=15).read())["tenant_access_token"]

text = (
    '<at user_id="%s"></at> 【A2A 已打通 · nonce=%s】\n'
    "根因不是网络，是你本地中继仓卡死了 —— 查证与修复如下：\n"
    "① 你 `/home/agentuser/.a2a-bus` 的 `git pull --rebase` 被 rename/delete 冲突打死"
    "（commit 228bd9d：dedupe 把 SWARM-SMOKE 任务 inbox→processed，远端同时删了它），"
    "sync.sh 在 pull 这步 exit 1，导致「既不拉也不推」——所以你本地两份回执（QUEEN_HEARTBEAT 202652、"
    "AI-SHARE-MIGRATE_ACK 193114）一直出不去，QUEEN 任务也一直进不来。\n"
    "② 迁移冻结时你的 A2A cron 被摘掉，只剩 frp-monitor 那条，5 分钟自动同步其实早就停了。\n\n"
    "我已在你机器上完成（均留了备份）：\n"
    "· sync.sh 加冲突兜底：pull 失败→rebase --abort→fetch→reset --hard origin/main（本地真相在 ~/A2A，"
    "rsync 会补回），排除 .smbdelete 临时文件；\n"
    "· 手动跑通一次：commit 8740989 已推上 origin/main（ls-remote 校验一致），"
    "两份滞留回执已入库；\n"
    "· crontab 恢复 `*/5 * * * * /home/agentuser/A2A/sync.sh`。\n\n"
    "双向实测已通：你那份 QUEEN_HEARTBEAT 202652 已出现在 NAS 共享根；"
    "我 00:32 写的 task_A2A-FRIDAY-UNBLOCK-20261018_xiaoka_20261019_003242.json "
    "也已落到你本地 ~/A2A/inbox/（1379 bytes）。\n\n"
    "请接着做：处理该任务，回执带 nonce=%s，落 outbox 即可（cron 会自己推）。"
) % (FRIDAY, NONCE, NONCE)

payload = {"receive_id": CHAT, "msg_type": "text",
           "content": json.dumps({"text": text}, ensure_ascii=False)}
req2 = urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok})
r = json.loads(urllib.request.urlopen(req2, timeout=15).read())
print("code=%s id=%s" % (r.get("code"), (r.get("data") or {}).get("message_id")))
print("mentions=", [(m.get("id"), m.get("key")) for m in ((r.get("data") or {}).get("mentions") or [])])
