"""nanoMuse 自建 relay 端到端验收：取码 -> 登录 -> 列模型 -> 真跑一次 chat。

用法：python3 relay_e2e.py [relay地址] [ssh主机]
默认 http://192.168.199.2:8795 与 DY@192.168.199.2。
"""
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.199.2:8795"
SSH = sys.argv[2] if len(sys.argv) > 2 else "DY@192.168.199.2"
CONTAINER = "cloud-relay-1"
IDENT = f"probe{int(time.time())}@local.test"


def post(path, body, tok=None, timeout=120):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            # /v1/auth/code 返回 204 无 body，解析必须容错
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]


print("1) auth/code ->", post("/v1/auth/code", {"identifier": IDENT})[0])

# 码 TTL 很短：取码后立刻取日志立刻验，别分两轮
logs = subprocess.run(
    ["ssh", "-o", "ConnectTimeout=10", SSH,
     f"sudo -n docker logs --tail 15 {CONTAINER} 2>&1 | tail -6"],
    capture_output=True, text=True, timeout=60,
).stdout
codes = re.findall(r"\b(\d{6})\b", logs)
print("2) 日志尾部:", logs.strip().replace("\n", " | ")[-160:])
if not codes:
    raise SystemExit("没取到验证码")

st, body = post("/v1/auth/verify", {"identifier": IDENT, "code": codes[-1], "device": "probe"})
print("3) auth/verify ->", st, list(body.keys()) if isinstance(body, dict) else body)
if st != 200:
    raise SystemExit(1)

# 凭据字段是 api_key，不是 token/access_token
tok = body.get("api_key")
if not tok:
    tok = next((v for v in body.values() if isinstance(v, str) and len(v) > 20), None)

req = urllib.request.Request(BASE + "/v1/models", headers={"Authorization": "Bearer " + tok})
with urllib.request.urlopen(req, timeout=30) as r:
    ids = [m["id"] for m in json.loads(r.read().decode()).get("data", [])]
print("4) /v1/models ->", len(ids), ids[:3])

pick = next((i for i in ids if "deepseek" in i), ids[0])
st, ans = post(
    "/v1/chat/completions",
    {"model": pick, "messages": [{"role": "user", "content": "只回四个字：通道正常"}], "max_tokens": 20},
    tok, timeout=180,
)
print("5) chat ->", st, "model=", pick)
print("   ", ans["choices"][0]["message"]["content"][:60] if st == 200 else str(ans)[:250])
