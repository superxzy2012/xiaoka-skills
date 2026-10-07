#!/usr/bin/env python3
"""
深滚动抓取主页全量作品。
🔴 只开 1 个标签，循环复用（BOSS 机器限制）
🔴 滚动到底后判重退出，避免无效循环
"""
import sys, json, time, re
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

SEC = sys.argv[1]
OUT = sys.argv[2]
MAX = int(sys.argv[3]) if len(sys.argv) > 3 else 200

GET = r"""
(()=>{const a=[...document.querySelectorAll("a[href*='/video/']")];
  return JSON.stringify(a.map(x=>x.getAttribute('href')))})()
"""

c = CDP()
try:
    c.new_tab("about:blank")
    c.goto(f"https://www.douyin.com/user/{SEC}", wait=12)
    seen, stall, empty = set(), 0, 0
    for i in range(MAX):
        raw = c.eval_js(GET)
        try:
            links = json.loads(raw) if isinstance(raw, str) else (raw or [])
        except Exception:
            links = []
        before = len(seen)
        for l in links:
            m = re.search(r"/video/(\d+)", l or "")
            if m:
                seen.add(m.group(1))
        gain = len(seen) - before
        # 页面高度，判断是否真到底
        h = c.eval_js("()=>document.body.scrollHeight")
        y = c.eval_js("()=>window.scrollY")
        try:
            at_bottom = (h and y and (y + 1400) >= h)
        except Exception:
            at_bottom = False
        print(f"  [{i+1:03d}] 本页{len(links):3d} +{gain:3d} 累计{len(seen):4d} "
              f"scrollY={y}/{h}{'  ←到底' if at_bottom else ''}")
        if gain == 0:
            stall += 1
            empty += 1
        else:
            stall = 0
            empty = 0
        if stall >= 3:
            print("  连续3次无新增，判定到底")
            break
        c.eval_js("window.scrollBy(0, 2400)")
        time.sleep(1.8)
    vids = sorted(seen)
    json.dump({"sec_uid": SEC, "videos": vids}, open(OUT, "w"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ 共 {len(vids)} 个作品 -> {OUT}")
finally:
    c.close()