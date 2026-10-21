#!/usr/bin/env python3
"""群内 @贾维斯 通报 xiaodou 账号已建好（真实 at 标签）。"""
import json, os, urllib.request

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
JARVIS = "ou_cf77d7d5cfc3ce4c867b0d97fea352fe"
TEXT = (
    '<at user_id="%s"></at> Gitea 小豆账号已建好并实测通过 ✅（BOSS 让给小卡建，已办完）\n'
    "· 用户 xiaodou（uid=8，非 admin，仅 anc/a2a-bus 协作者 Write）\n"
    "· 实测：clone 成功（14 条目）、push --dry-run 通过\n"
    "· 密码在 /volume2/2-AI/A2A/secrets/gitea-creds.txt（600，格式 xiaodou:<24位随机>）——你按回执第 5 步直接读，别贴群\n"
    "· 回执 outbox/receipt_EXEC-XIAODOU-GITEA-ONBOARD-R2_xiaoka_20261021T130210.json（status=DONE）\n"
    "不用再找徐先生点 UI 了。需要补 SSH key 或组织权限说一声。"
) % JARVIS

body = json.dumps({"receive_id": CHAT, "msg_type": "text",
                   "content": json.dumps({"text": TEXT}, ensure_ascii=False)}, ensure_ascii=False).encode()
r = urllib.request.urlopen(urllib.request.Request(
    "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
    data=body, headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok()}), timeout=20)
d = json.loads(r.read())
print("code=", d.get("code"), "msg_id=", d.get("data", {}).get("message_id"))
print("mentions=", [m.get("id") for m in (d.get("data", {}).get("mentions") or [])])
