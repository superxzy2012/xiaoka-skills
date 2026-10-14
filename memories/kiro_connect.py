#!/usr/bin/env python3
"""Kiro 设备码授权 —— 生成码 + 轮询直到授权成功。

用法:
  python3 kiro_connect.py new     # 生成新设备码，打印要 BOSS 点的 URL
  python3 kiro_connect.py wait    # 轮询等待授权完成（用上次生成的码）
"""
import json
import sys
import time
import urllib.error
import urllib.request

BASE = "http://192.168.199.2:20128"
STATE = "/opt/data/cache/scratch/omni/kiro_dev.json"


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=40) as r:
        return json.loads(r.read().decode())


def new_code():
    d = get("/api/oauth/kiro/device-code")
    json.dump(d, open(STATE, "w"))
    print("user_code :", d.get("user_code"))
    print("URL       :", d.get("verification_uri_complete"))
    print("expires_in:", d.get("expires_in"), "s")
    return d


def wait(deadline_s=900):
    d = json.load(open(STATE))
    body = {
        "deviceCode": d["device_code"],
        "codeVerifier": d["codeVerifier"],
        "extraData": {
            "_clientId": d["_clientId"],
            "_clientSecret": d["_clientSecret"],
            "_region": d["_region"],
            "_authMethod": d["_authMethod"],
        },
    }
    end = time.time() + deadline_s
    while time.time() < end:
        code, res = post("/api/oauth/kiro/poll", body)
        if res.get("success"):
            print("✅ 授权成功:", json.dumps(res, ensure_ascii=False)[:600])
            return res
        err = res.get("error")
        if err == "slow_down":
            time.sleep(5)
            continue
        if res.get("pending") or err in ("authorization_pending", "invalid_client"):
            # invalid_client 偶发：继续轮询即可
            print(f"  …pending ({err})")
            time.sleep(4)
            continue
        print("❌ 失败:", json.dumps(res, ensure_ascii=False)[:400])
        return None
    print("⏱ 超时（码已过期，用 new 重新生成）")
    return None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "new"
    if cmd == "new":
        new_code()
    else:
        wait()
