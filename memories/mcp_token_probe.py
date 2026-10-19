#!/usr/bin/env python3
"""拉管理群最近消息，筛出含 mcp/token 的发言。"""
import json, os, sys, urllib.request, urllib.parse

def env(p='/opt/data/.env'):
    d = {}
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip().strip('"\'')
    return d

E = env()
BASE = 'https://open.feishu.cn/open-apis'
def post(path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=15).read())

tok = post('/auth/v3/tenant_access_token/internal',
           {'app_id': E['FEISHU_APP_ID'], 'app_secret': E['FEISHU_APP_SECRET']})['tenant_access_token']

chat = sys.argv[1] if len(sys.argv) > 1 else 'oc_568730200f9a3120919be177344687e5'
kw = (sys.argv[2] if len(sys.argv) > 2 else 'mcp token').lower().split(',')
q = urllib.parse.urlencode({'container_id': chat, 'container_id_type': 'chat',
                            'sort_type': 'ByCreateTimeDesc', 'page_size': 50})
req = urllib.request.Request(BASE + '/im/v1/messages?' + q,
                             headers={'Authorization': 'Bearer ' + tok})
d = json.loads(urllib.request.urlopen(req, timeout=20).read())
items = d.get('data', {}).get('items', [])
print(f"取到 {len(items)} 条消息")
import datetime
for m in items:
    body = m.get('body', {}).get('content', '')
    try:
        txt = json.loads(body).get('text', body)
    except Exception:
        txt = body
    if any(k in txt.lower() for k in kw):
        ts = datetime.datetime.fromtimestamp(int(m['create_time']) / 1000).strftime('%m-%d %H:%M')
        print(f"[{ts}] {m.get('sender',{}).get('id','?')} {m.get('msg_type')}: {txt[:500]}")
        print('   msg_id', m.get('message_id'))
