#!/usr/bin/env python3
"""把 NAS 上的 token 文件投递到星期五 VM 的本地 ~/A2A/secrets/（不入 git），并做云端实测。"""
import subprocess, base64, json, urllib.request

SSH = ['ssh', '-i', '/opt/data/.ssh/id_ed25519', '-o', 'StrictHostKeyChecking=no',
       '-o', 'UserKnownHostsFile=/dev/null']

def run(host, cmd, timeout=60):
    p = subprocess.run(SSH + [host, cmd], capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout.strip(), p.stderr.strip()[-200:]

rc, b64, err = run('DY@192.168.199.2', 'base64 -w0 /volume2/2-AI/A2A/secrets/mcp-token-friday.md')
print('取 token 文件 rc=', rc, 'b64 长度=', len(b64))
if rc != 0:
    raise SystemExit('读 NAS secrets 失败: ' + err)

content = base64.b64decode(b64).decode()
tok = [l.strip() for l in content.split('\n') if l.startswith('xkfr_')][0]
print('token 前缀=', tok[:9], '总长=', len(tok))

cmd = ('mkdir -p ~/A2A/secrets && chmod 700 ~/A2A/secrets && '
       f'printf %s {b64} | base64 -d > ~/A2A/secrets/mcp-token-friday.md && '
       'chmod 600 ~/A2A/secrets/mcp-token-friday.md && '
       'ls -l ~/A2A/secrets/ && echo "=== sync 目录清单 ===" && sed -n "1,20p" ~/A2A/sync.sh')
rc, out, err = run('agentuser@100.66.1.6', cmd)
print('投递 rc=', rc)
print(out[-700:])
if err:
    print('ERR', err)

# 云端用该 token 实测 MCP 握手 + tools/list
probe = f'''import json,urllib.request,urllib.error
T={tok!r}
def post(port,body,sid=None):
    h={{"Content-Type":"application/json","Accept":"application/json, text/event-stream","Authorization":"Bearer "+T}}
    if sid: h["Mcp-Session-Id"]=sid
    r=urllib.request.Request("http://100.66.1.7:%d/mcp"%port,data=json.dumps(body).encode(),headers=h)
    try:
        resp=urllib.request.urlopen(r,timeout=12); return resp.status,resp.headers.get("Mcp-Session-Id"),resp.read().decode()[:200]
    except urllib.error.HTTPError as e: return e.code,None,e.read().decode()[:200]
for port in (3456,3458):
    st,sid,b=post(port,{{"jsonrpc":"2.0","id":1,"method":"initialize","params":{{"protocolVersion":"2025-06-18","capabilities":{{}},"clientInfo":{{"name":"friday-check","version":"1"}}}}}})
    print("port %d initialize -> %s session=%s"%(port,st,(sid or "")[:10]))
    if sid:
        st2,_,b2=post(port,{{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{{}}}},sid)
        print("port %d tools/list -> %s 工具数=%d"%(port,st2,b2.count(chr(34)+"name"+chr(34))))
'''
pb64 = base64.b64encode(probe.encode()).decode()
cmd2 = (f'printf %s {pb64} | base64 -d > /tmp/mcp_check.py && python3 /tmp/mcp_check.py; rm -f /tmp/mcp_check.py')
rc, out, err = run('agentuser@100.66.1.6', cmd2)
print('云端实测 rc=', rc)
print(out)
if err:
    print('ERR', err)
