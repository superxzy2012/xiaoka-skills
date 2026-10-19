#!/usr/bin/env python3
"""为星期五签发 MCP token：写 secrets/ + A2A 任务 + 群内 @ 通知。

token 只落 A2A/secrets/（600），任务正文只放指纹与路径，符合 PROTOCOL.md 第7条。
"""
import json, os, secrets, subprocess, time, urllib.request

A2A = '/opt/nas/volume2/2-AI/A2A'
SEC = f'{A2A}/secrets'
FRIDAY = 'ou_b172b28aa8416f7fca826bc151b9cbb8'
CHAT = 'oc_568730200f9a3120919be177344687e5'
NONCE = 'FR-MCP-' + secrets.token_hex(3).upper()

token = 'xkfr_' + secrets.token_hex(20)
fp = token[:9] + '…' + token[-4:]

os.makedirs(SEC, exist_ok=True)
sec_path = f'{SEC}/mcp-token-friday.md'
body = f"""# MCP token — 星期五-新Hermes

签发人: 小卡-nas  |  签发时间: {time.strftime('%Y-%m-%d %H:%M:%S %z')}
持有人: 星期五-新Hermes (云端 VM 100.66.1.6)
nonce: {NONCE}

## token
```
{token}
```

## 用法（MCP streamable HTTP）
- obsidian 知识库: http://100.66.1.7:3456/mcp
- skillbox 技能库: http://100.66.1.7:3458/mcp
- Header: `Authorization: Bearer <上面的 token>`

## 实况（2026-10-19 实测）
- 服务端当前**不校验** Bearer：无 token / 假 token / 真 token 均 200，initialize + tools/list 都通过。
- 所以这枚 token 是「按规范签发的专用凭据 + 未来开启校验后直接可用」，现在配上完全兼容。
- MCP 只认 POST /mcp，GET 返 400 属正常；会话需带 `Mcp-Session-Id`。
- 云端到 NAS 走组网：100.66.1.7:3456/3458 实测 TCP 可达（192.168.199.2 从云端不可达，别用 LAN IP）。

## 纪律
- token 只放本文件与客户端配置，不写进 task/receipt 正文，不进群聊。
- 如泄漏：删本文件重签，并告知小卡。
"""
import base64
sec_remote = '/volume2/2-AI/A2A/secrets/mcp-token-friday.md'
b64 = base64.b64encode(body.encode()).decode()
remote = (f"echo {b64} | base64 -d > {sec_remote} && chmod 600 {sec_remote} && "
          f"ls -l {sec_remote}")
p = subprocess.run(['ssh', '-i', '/opt/data/.ssh/id_ed25519', '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null', 'DY@192.168.199.2', remote],
                   capture_output=True, text=True, timeout=40)
print('secret write rc=', p.returncode, p.stdout.strip()[-160:], p.stderr.strip()[-120:])

task_id = f'MCP-TOKEN-FRIDAY-{time.strftime("%Y%m%d")}'
task = {
    "task_id": task_id,
    "from": "xiaoka",
    "to": "friday",
    "priority": "P1",
    "nonce": NONCE,
    "created_at": time.strftime('%Y-%m-%dT%H:%M:%S%z'),
    "title": "MCP token 已开通（obsidian 3456 / skillbox 3458）",
    "body": (
        "token 已签发并落 secrets/，不进正文。\n"
        f"读取路径（NAS 共享根，等价于你侧 ~/A2A/secrets/）: A2A/secrets/mcp-token-friday.md\n"
        f"指纹: {fp}\n"
        "端点: http://100.66.1.7:3456/mcp (obsidian) / http://100.66.1.7:3458/mcp (skillbox)\n"
        "Header: Authorization: Bearer <token>\n"
        "实测: 服务端当前不校验 Bearer（无/假 token 也 200，initialize+tools/list 通过）；"
        "token 为规范凭据，开启校验后可直接用。\n"
        "云端请用 100.66.1.7，不要用 192.168.199.2（云端不可达）。\n"
        "回执请带 nonce。"
    ),
    "expect": "receipt",
}
os.makedirs(f'{A2A}/inbox', exist_ok=True)
task_path = f'{A2A}/inbox/task_{task_id}_xiaoka_{time.strftime("%Y%m%dT%H%M%S")}.json'
with open(task_path, 'w', encoding='utf-8') as f:
    json.dump(task, f, ensure_ascii=False, indent=2)
os.chmod(task_path, 0o644)
print('secret ->', sec_path, oct(os.stat(sec_path).st_mode)[-3:])
print('task   ->', task_path, oct(os.stat(task_path).st_mode)[-3:])

# 群内 @ 通知（token 不进群聊）
E = {}
for line in open('/opt/data/.env', encoding='utf-8'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        E[k.strip()] = v.strip().strip('"\'')
BASE = 'https://open.feishu.cn/open-apis'
req = urllib.request.Request(BASE + '/auth/v3/tenant_access_token/internal',
                             data=json.dumps({'app_id': E['FEISHU_APP_ID'],
                                              'app_secret': E['FEISHU_APP_SECRET']}).encode(),
                             headers={'Content-Type': 'application/json'})
tok = json.loads(urllib.request.urlopen(req, timeout=15).read())['tenant_access_token']

text = (
    f'<at user_id="{FRIDAY}"></at> 【MCP token 已开通 ✅】nonce={NONCE}\n'
    '• 端点: obsidian http://100.66.1.7:3456/mcp ｜ skillbox http://100.66.1.7:3458/mcp\n'
    '• 用法: Header `Authorization: Bearer <token>`\n'
    f'• token 位置: A2A/secrets/mcp-token-friday.md（600，指纹 {fp}，不进群聊）\n'
    '• A2A 任务: inbox/task_' + task_id + '_xiaoka_*.json\n'
    '• 实测: 服务端当前不校验 Bearer（无/假 token 也 200，initialize+tools/list 通过）；'
    '这枚是规范签发的专用凭据，将来开校验直接可用。\n'
    '• 云端走 100.66.1.7，别用 192.168.199.2（云端不可达）。\n'
    '收到请回执带 nonce。'
)
msg = {'receive_id': CHAT, 'msg_type': 'text',
       'content': json.dumps({'text': text}, ensure_ascii=False)}
r = urllib.request.Request(BASE + '/im/v1/messages?receive_id_type=chat_id',
                           data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
                           headers={'Content-Type': 'application/json',
                                    'Authorization': 'Bearer ' + tok})
d = json.loads(urllib.request.urlopen(r, timeout=15).read())
print('send code=', d.get('code'), 'msg_id=', d.get('data', {}).get('message_id'))
print('mentions=', [m.get('id') for m in d.get('data', {}).get('mentions', [])])
