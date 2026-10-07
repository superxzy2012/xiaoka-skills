#!/usr/bin/env python3
"""逐条打开作品页，验证作者昵称，只保留属于目标账号的。"""
import sys, json, time, re
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

WANT = sys.argv[1]              # 目标昵称
SRC = sys.argv[2]               # 含 videos 列表的 json
OUT = sys.argv[3]               # 输出
SEC_HINT = sys.argv[4] if len(sys.argv) > 4 else None

ids = json.load(open(SRC))["videos"]

JS = r"""
(()=>{
  const a=[...document.querySelectorAll("a[href*='/user/']")]
    .map(x=>({h:x.getAttribute('href')||'', t:(x.innerText||'').trim()}))
    .filter(x=>x.h.includes('MS4w'));
  const first=a[0]||{h:'',t:''};
  const h=document.documentElement.innerHTML;
  const g=re=>(h.match(re)||[])[1]||'';
  return JSON.stringify({
    nick: first.t || g(/"nickname":"([^"]+)/),
    sec: (first.h.match(/\/user\/(MS4[A-Za-z0-9_-]+)/)||[])[1]||'',
    title: g(/"desc":"([^"]{0,120})/),
    dur: g(/"duration":(\d+)/),
    fav: g(/"digg_count":(\d+)/),
    date: g(/"create_time":(\d+)/)
  })})()
"""

c = CDP()
keep, drop, nodata = [], [], []
try:
    for i, aid in enumerate(ids, 1):
        try:
            c.goto(f"https://www.douyin.com/video/{aid}", wait=7)
            raw = c.eval_js(JS)
            if not raw:
                # 页面未就绪，重试一次再放弃
                time.sleep(2.5)
                c.goto(f"https://www.douyin.com/video/{aid}", wait=8)
                raw = c.eval_js(JS)
            if not raw:
                nodata.append({"id": aid, "err": "eval_js 返回 None（页面未渲染）"})
                print(f"[{i}/{len(ids)}] {aid} ⚠️ 页面未渲染")
                time.sleep(2)
                continue
            d = json.loads(raw if isinstance(raw, str) else raw)
            sec_ok = (not SEC_HINT) or (d.get("sec") == SEC_HINT)
            name_ok = WANT in (d.get("nick") or "")
            rec = {"id": aid, **d}
            if sec_ok and name_ok:
                keep.append(rec)
            else:
                drop.append(rec)
            print(f"[{i}/{len(ids)}] {aid}  {'✅' if (sec_ok and name_ok) else '❌'} "
                  f"{(d.get('nick') or '?')[:16]:18} {(d.get('title') or '')[:34]}")
        except Exception as e:
            nodata.append({"id": aid, "err": str(e)[:80]})
            print(f"[{i}/{len(ids)}] {aid} ⚠️ {type(e).__name__}")
        time.sleep(1.4)
finally:
    c.close()
    json.dump({"keep": keep, "drop": drop, "nodata": nodata},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ 属于本号: {len(keep)}  不属于: {len(drop)}  无数据: {len(nodata)} -> {OUT}")