#!/usr/bin/env python3
"""逐条开新标签验证作品作者归属。"""
import sys, json, time
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

WANT = sys.argv[1]
SRC = sys.argv[2]
OUT = sys.argv[3]
SEC = sys.argv[4] if len(sys.argv) > 4 else None

ids = json.load(open(SRC))["videos"]

JS = r"""
(()=>{
  const h = document.documentElement.innerHTML;
  const g = re => (h.match(re)||[])[1] || '';
  // 作者卡片（页面第一个 /user/MS4w 链接）
  const a = [...document.querySelectorAll("a[href*='/user/MS4w']")]
            .map(x=>({h:x.getAttribute('href')||'', t:(x.innerText||'').trim()}))[0] || {};
  return JSON.stringify({
    nick: a.t || g(/"nickname":"([^"]+)/),
    sec:  (a.h.match(/\/user\/(MS4[A-Za-z0-9_-]+)/)||[])[1] || '',
    title: g(/"desc":"([^"]{0,110})/),
    dur:   g(/"duration":(\d+)/),
    fav:   g(/"digg_count":(\d+)/),
    date:  g(/"create_time":(\d+)/),
    ok:    document.title.length
  })})()
"""

keep, drop, nodata = [], [], []
c = CDP()
try:
    for i, aid in enumerate(ids, 1):
        rec = None
        for attempt in (1, 2):
            try:
                c.new_tab("about:blank")
                c.goto(f"https://www.douyin.com/video/{aid}", wait=11)
                raw = c.eval_js(JS)
                if raw:
                    d = json.loads(raw if isinstance(raw, str) else raw)
                    rec = {"id": aid, **d}
                    break
            except Exception as e:
                err = f"{type(e).__name__}: {str(e)[:60]}"
            time.sleep(2)
        if not rec:
            nodata.append({"id": aid})
            print(f"[{i}/{len(ids)}] {aid} ⚠️ 未渲染")
            continue
        ok = (SEC and rec.get("sec") == SEC) or (WANT in (rec.get("nick") or ""))
        (keep if ok else drop).append(rec)
        print(f"[{i}/{len(ids)}] {aid} {'✅' if ok else '❌'} "
              f"{(rec.get('nick') or '?')[:14]:16} {(rec.get('title') or '')[:36]}")
        time.sleep(2.5)
finally:
    c.close()
    json.dump({"keep": keep, "drop": drop, "nodata": nodata},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ 本号 {len(keep)}  非本号 {len(drop)}  无数据 {len(nodata)} -> {OUT}")