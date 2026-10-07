#!/usr/bin/env python3
"""清理：关闭我打开的抖音标签 + 列出当前所有标签，人工核对哪些是 BOSS 的。"""
import sys, json, urllib.request

BASE = "http://192.168.199.184:9224"

def targets():
    with urllib.request.urlopen(f"{BASE}/json/list", timeout=10) as r:
        return json.loads(r.read().decode())

ts = targets()
print(f"当前共 {len(ts)} 个标签：\n")
for t in ts:
    url = t.get("url", "")
    kind = "🔴抖音" if "douyin.com" in url else ("🟡B站" if "bilibili" in url else "⚪其他")
    print(f"  [{t.get('id')[:8]}] {kind} {t.get('type','?'):8} {url[:78]}")

# 关掉所有抖音标签（douyin.com 的都是我开的，BOSS 自己不刷抖音网页版）
douyin = [t for t in ts if "douyin.com" in t.get("url", "")]
print(f"\n抖音标签 {len(douyin)} 个，准备全部关闭")
for t in douyin:
    tid = t.get("id")
    try:
        with urllib.request.urlopen(
            urllib.request.Request(f"{BASE}/json/close/{tid}"), timeout=6) as r:
            r.read()
        print(f"  ✅ 已关 {tid[:8]} {t['url'][:60]}")
    except Exception as e:
        print(f"  ❌ {tid[:8]} {e}")

time_left = None
with urllib.request.urlopen(f"{BASE}/json/list", timeout=10) as r:
    time_left = json.loads(r.read().decode())
print(f"\n剩余标签 {len(time_left)} 个：")
for t in time_left:
    print(f"  {t.get('url','')[:85]}")