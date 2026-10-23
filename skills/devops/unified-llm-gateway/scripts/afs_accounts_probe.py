#!/usr/bin/env python3
"""AFS(Chat2API) 账户实证探针 —— 回答「某供应商到底有没有登录态」。

用法（宿主机）：
    base64 -w0 afs_accounts_probe.py | ssh ... 'base64 -d > /tmp/p.py'
    sudo -n docker cp /tmp/p.py chat2api:/tmp/ && sudo -n docker exec chat2api python3 /tmp/p.py

为什么要这个脚本：/v1/models 列的是 modelMappings（映射表），没有账号也会列出来，
照着模型名回答「X 能用」会误导 BOSS。唯一可信来源是 data.json 的 accounts。

绝不打印任何 token / refresh_token / secret 的值，只打印凭据键名和长度。
"""
import json
import os
import sys
import time

CANDIDATES = [
    "/root/.chat2api/data.json",              # AFS / chat2api 1.6.0
    "/root/.config/chat2api/data.json",       # 1.4.0
    "/root/.chat2api/config.json",
]


def find_data_file():
    if len(sys.argv) > 1:
        return sys.argv[1]
    for p in CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def as_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, dict):
        return [dict(v=k, **(val if isinstance(val, dict) else {"value": val})) for k, val in v.items()]
    return []


def main():
    p = find_data_file()
    if not p:
        print("找不到 data.json，候选路径都不存在：", CANDIDATES)
        return 2
    print(f"data.json = {p}  ({os.path.getsize(p)} B)")
    d = json.load(open(p))
    cfg = d.get("config", d)

    now_ms = time.time() * 1000
    accs = as_list(d.get("accounts") or cfg.get("accounts"))
    print(f"\n=== accounts: {len(accs)} 个 ===")
    by_prov = {}
    for a in accs:
        if not isinstance(a, dict):
            continue
        prov = a.get("providerId") or a.get("provider") or "?"
        by_prov[prov] = by_prov.get(prov, 0) + 1
        name = a.get("name") or a.get("email") or a.get("id") or "?"
        creds = a.get("credentials") or {}
        keys = ",".join(f"{k}({len(str(v))})" for k, v in creds.items()) if isinstance(creds, dict) else "?"
        exp = a.get("expiresAt") or (creds.get("expires_at") if isinstance(creds, dict) else None)
        left = ""
        if isinstance(exp, (int, float)) and exp > 0:
            left = f"剩{(exp - now_ms)/3600000:.1f}h" if exp > now_ms else "已过期"
        en = a.get("enabled")
        print(f"  {prov:10s} {str(name)[:28]:28s} enabled={en} creds=[{keys}] {left}")

    print("\n按供应商汇总：", by_prov or "(无)")

    maps = cfg.get("modelMappings") or {}
    if isinstance(maps, dict) and maps:
        pref = {}
        for k, v in maps.items():
            pid = (v or {}).get("preferredProviderId") or "-"
            pref[pid] = pref.get(pid, 0) + 1
        print(f"\n=== modelMappings: {len(maps)} 条，按 preferredProviderId ===")
        for pid, n in sorted(pref.items(), key=lambda x: -x[1]):
            mark = "" if pid in by_prov or pid in ("-", "") else "  <-- 无对应账号，调用会失败"
            print(f"  {pid:12s} {n} 条{mark}")

    print("\n=== 关键开关 ===")
    mg = cfg.get("managementApi") or {}
    print(f"  autoStartProxy     = {cfg.get('autoStartProxy')}   (false 时容器重启后 8080 不自启，网关全 502)")
    print(f"  enableManagementApi= {mg.get('enableManagementApi')}  (管理路由挂在 8080 的 /v0/management/，不是 19825)")
    print(f"  managementApiSecret= {'[SET]' if mg.get('managementApiSecret') else '[EMPTY]'}")
    tc = cfg.get("toolCallingConfig") or {}
    print(f"  toolCalling.clientAdapterId = {tc.get('clientAdapterId')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
