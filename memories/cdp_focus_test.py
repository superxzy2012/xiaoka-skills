#!/usr/bin/env python3
"""验证 new_tab(background=True) 是否真的不抢前台焦点。"""
import sys, json, urllib.request, time
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP
BASE = "http://192.168.199.184:9224"


def active_tab():
    """拿当前前台激活的标签 URL"""
    with urllib.request.urlopen(f"{BASE}/json/list", timeout=8) as r:
        ts = json.loads(r.read().decode())
    for t in ts:
        if t.get("type") == "page" and t.get("url", "").startswith(("http", "chrome")):
            pass
    # 用 CDP 的 Target.getTargets + 前台判定：靠 order 不可靠，改用 /json/activate 副作用法
    return [t.get("url", "")[:60] for t in ts if t.get("type") == "page"]


print("【before】打开的标签：")
for u in active_tab():
    print("   ", u)

c = CDP()
try:
    tid = c.new_tab("https://www.douyin.com/explore", background=True)
    print(f"\n✅ 后台标签已建: {tid[:8]}")
    time.sleep(5)
    print("\n【after 建标签后】标签列表：")
    for u in active_tab():
        print("   ", u)
    # 导航测试
    c.goto("https://www.bilibili.com/", wait=5)
    print("\n【after 导航 bilibili】标签列表：")
    for u in active_tab():
        print("   ", u)
finally:
    c.close()
    time.sleep(1)
    print("\n【收尾后】标签列表：")
    for u in active_tab():
        print("   ", u)