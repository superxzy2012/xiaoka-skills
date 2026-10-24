#!/usr/bin/env python3
"""从已登录的 Hyperbrowser 控制台页面内存里挖完整 API key（不依赖剪贴板/焦点）。

用法: python grab_key.py [CDP_BASE] [OUT_PATH]
前提: 已有到目标 Chrome 的 CDP 隧道（如 127.0.0.1:9223）。
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, "/opt/data/memories")
from cdp import CDP  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:9223"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/opt/data/cache/scratch/hb_key.txt"

FIND = r"""(() => {
  const hit = new Set();
  const re = /hb_[A-Za-z0-9_-]{16,}/g;
  const scan = (s) => { if (typeof s === 'string') { const m = s.match(re); if (m) m.forEach(x=>hit.add(x)); } };
  for (const st of [localStorage, sessionStorage]) {
    try { for (let i=0;i<st.length;i++) scan(st.getItem(st.key(i))); } catch(e){}
  }
  const roots = [...document.querySelectorAll('#root,#__next,body > div')];
  const seen = new Set();
  const walk = (fiber, depth) => {
    if (!fiber || depth > 60 || seen.has(fiber)) return;
    seen.add(fiber);
    try {
      const p = fiber.memoizedProps;
      if (p && typeof p === 'object') for (const k in p) scan(p[k]);
      if (typeof fiber.memoizedState === 'string') scan(fiber.memoizedState);
      if (fiber.memoizedState && typeof fiber.memoizedState === 'object')
        for (const k in fiber.memoizedState) scan(fiber.memoizedState[k]);
    } catch(e){}
    walk(fiber.child, depth+1);
    walk(fiber.sibling, depth+1);
  };
  for (const r of roots) {
    const k = Object.keys(r).find(k => k.startsWith('__reactFiber$') || k.startsWith('__reactContainer$'));
    if (k) walk(r[k], 0);
  }
  return [...hit].join('\n');
})()"""

lst = json.load(urllib.request.urlopen(BASE + "/json/list", timeout=10))
t = next((x for x in lst if x.get("type") == "page" and "hyperbrowser" in (x.get("url") or "")), None)
if not t:
    print("NO TARGET (需先打开 app.hyperbrowser.ai)")
    sys.exit(2)

with CDP(url=BASE) as c:
    sid = c.call("Target.attachToTarget", {"targetId": t["id"], "flatten": True})["result"]["sessionId"]
    r = c.call("Runtime.evaluate", {"expression": FIND, "returnByValue": True, "awaitPromise": True}, sid=sid, tmo=30)
    found = (r or {}).get("result", {}).get("result", {}).get("value") or ""

cands = [x for x in found.split("\n") if x.startswith("hb_") and "•" not in x and len(x) >= 30]
if not cands:
    print("no full key in page memory")
    sys.exit(3)

best = max(cands, key=len)
with open(OUT, "w") as f:
    f.write(best)
os.chmod(OUT, 0o600)
print("saved ->", OUT, "| len:", len(best), "|", best[:10] + "..." + best[-4:])
