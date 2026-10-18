#!/usr/bin/env python3
"""
深滚动抓取主页全量作品。
🔴 只开 1 个标签，循环复用（BOSS 机器限制）
🔴 后台标签必须开 focus emulation，否则 Chrome 节流渲染 → 虚拟列表不加载，
   只会拿到第一屏 ~28 条（2026-10-17 实测：开 focus emulation 后 27→63→135→243 条）
🔴 滚的是页面里的滚动容器，不是 window（抖音主页 window 不滚）
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

# 滚真正的列表容器（overflow scroll/auto 且可滚距离最大者），返回 scrollTop/scrollHeight
SCROLL_GRID = r"""
(()=>{
  let b=null, g=0;
  for (const e of document.querySelectorAll('div,main,section')) {
    const s=getComputedStyle(e);
    if (s.overflowY==='scroll' || s.overflowY==='auto') {
      const d=e.scrollHeight-e.clientHeight;
      if (d>g) { g=d; b=e; }
    }
  }
  if (!b) return 'no-grid';
  b.scrollTop = b.scrollHeight;
  return Math.round(b.scrollTop)+'/'+b.scrollHeight;
})()
"""

c = CDP()
try:
    c.new_tab("about:blank", background=True)
    # 关键：让后台标签像前台一样渲染，否则虚拟列表永不加载第二屏
    try:
        c.call("Emulation.setFocusEmulationEnabled", {"enabled": True}, c._sid)
    except Exception as e:
        print(f"  ⚠️ focus emulation 开启失败（可能只拿到第一屏）: {e}")
    c.goto(f"https://www.douyin.com/user/{SEC}", wait=12)
    seen, stall = set(), 0
    last_pos = ""
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
        pos = c.eval_js(SCROLL_GRID)
        stuck = (pos == last_pos and pos not in (None, "no-grid"))
        last_pos = pos
        print(f"  [{i+1:03d}] 本页{len(links):4d} +{gain:3d} 累计{len(seen):4d} scroll={pos}"
              f"{'  ←滚不动' if stuck else ''}")
        if gain == 0:
            stall += 1
        else:
            stall = 0
        if stall >= 3 or (stuck and gain == 0):
            print("  连续无新增，判定到底")
            break
        time.sleep(1.8)
    vids = sorted(seen)
    json.dump({"sec_uid": SEC, "videos": vids}, open(OUT, "w"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ 共 {len(vids)} 个作品 -> {OUT}")
finally:
    c.close()
