#!/usr/bin/env python3
"""
深滚动抓主页全量作品（修正版）。
🔴 抖音主页用「虚拟滚动容器」，window.scrollBy 无效，
   必须找到真正滚动的那个元素（或直接翻页参数）。
🔴 只开 1 个标签，全程复用。
"""
import sys, json, time, re
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

SEC = sys.argv[1]
OUT = sys.argv[2]
MAX = int(sys.argv[3]) if len(sys.argv) > 3 else 300

GET = r"""
(()=>{const a=[...document.querySelectorAll("a[href*='/video/']")];
  return JSON.stringify(a.map(x=>x.getAttribute('href')))})()
"""

# 找出真正可滚动的容器
FIND = r"""
(()=>{
  const cands=[...document.querySelectorAll('div,main,section')]
    .filter(e=>e.scrollHeight > e.clientHeight + 100);
  const info=cands.slice(0,6).map(e=>({
    tag:e.tagName, cls:(e.className||'').toString().slice(0,40),
    sh:e.scrollHeight, ch:e.clientHeight, st:e.scrollTop
  }));
  return JSON.stringify({n:cands.length, list:info,
    win:{sh:document.body.scrollHeight, ih:window.innerHeight, y:window.scrollY}})
})()
"""

SCROLL = r"""
(()=>{
  const cands=[...document.querySelectorAll('div,main,section')]
    .filter(e=>e.scrollHeight > e.clientHeight + 100);
  const el=cands.sort((a,b)=>b.scrollHeight-a.scrollHeight)[0];
  if(!el) { window.scrollBy(0,2400); return 'window'; }
  el.scrollTop = el.scrollTop + 2000;
  el.dispatchEvent(new Event('scroll',{bubbles:true}));
  return 'el:'+el.scrollTop+'/'+el.scrollHeight;
})()
"""

c = CDP()
try:
    c.new_tab("about:blank")
    c.goto(f"https://www.douyin.com/user/{SEC}", wait=14)
    print("滚动容器:", c.eval_js(FIND))
    seen, stall = set(), 0
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
        pos = c.eval_js(SCROLL)
        print(f"  [{i+1:03d}] 本页{len(links):3d} +{gain:3d} 累计{len(seen):4d}  {pos}")
        stall = stall + 1 if gain == 0 else 0
        if stall >= 4:
            print("  连续4次无新增，到底")
            break
        time.sleep(1.7)
    vids = sorted(seen)
    json.dump({"sec_uid": SEC, "videos": vids}, open(OUT, "w"),
              ensure_ascii=False, indent=1)
    print(f"\n✅ 共 {len(vids)} 个作品 -> {OUT}")
finally:
    c.close()