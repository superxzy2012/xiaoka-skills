import json, urllib.request, urllib.error, os, subprocess

# 1) 文件投递确认
p = subprocess.run(['ssh', '-i', '/opt/data/.ssh/id_ed25519', '-o', 'StrictHostKeyChecking=no',
                    '-o', 'UserKnownHostsFile=/dev/null', 'agentuser@100.66.1.6',
                    'ls -l ~/A2A/secrets/ && head -c 40 ~/A2A/secrets/mcp-token-friday.md'],
                   capture_output=True, text=True, timeout=40)
print('[VM secrets]', p.stdout.strip().replace('\n', ' | '))

tok = None
_p = subprocess.run(['ssh', '-i', '/opt/data/.ssh/id_ed25519', '-o', 'StrictHostKeyChecking=no',
                     '-o', 'UserKnownHostsFile=/dev/null', 'DY@192.168.199.2',
                     'cat /volume2/2-AI/A2A/secrets/mcp-token-friday.md'],
                    capture_output=True, text=True, timeout=40)
for line in _p.stdout.split('\n'):
    if line.strip().startswith('xkfr_'):
        tok = line.strip()
print('token 长度', len(tok) if tok else 'READ-FAIL')

def post(port, body, sid=None):
    h = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
         'Authorization': 'Bearer ' + tok}
    if sid:
        h['Mcp-Session-Id'] = sid
    r = urllib.request.Request(f'http://192.168.199.2:{port}/mcp',
                               data=json.dumps(body).encode(), headers=h)
    try:
        resp = urllib.request.urlopen(r, timeout=15)
        return resp.status, resp.headers.get('Mcp-Session-Id'), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, None, e.read().decode()

def sse_json(text):
    out = []
    for chunk in text.split('\n'):
        if chunk.startswith('data: '):
            try:
                out.append(json.loads(chunk[6:]))
            except Exception:
                pass
    return out

for port in (3456, 3458):
    st, sid, body = post(port, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                           "clientInfo": {"name": "xiaoka-verify", "version": "1"}}})
    info = (sse_json(body) or [{}])[0].get('result', {}).get('serverInfo', {})
    print(f'{port} init {st} serverInfo={info}')
    if sid:
        st2, _, b2 = post(port, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, sid)
        tools = (sse_json(b2) or [{}])[0].get('result', {}).get('tools', [])
        print(f'{port} tools/list {st2} 工具数={len(tools)} 前5={[t["name"] for t in tools[:5]]}')
