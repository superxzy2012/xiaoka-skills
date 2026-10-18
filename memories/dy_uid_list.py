#!/usr/bin/env python3
"""已知 sec_uid → 抓主页全部作品 ID（含滚动加载）。"""
import sys, json, time, re
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

UID = sys.argv[1]
MAXROLL = int(sys.argv[2]) if len(sys.argv) > 2 else 60
OUT = f"/opt/data/cache/scratch/dyprof_{UID[:12]}.json"

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
    # 后台开标签（BOSS 要求绝不抢焦点）+ focus emulation（否则后台节流，只拿到第一屏）
    c.new_tab("about:blank", background=True)
    try:
        c.call("Emulation.setFocusEmulationEnabled", {"enabled": True}, c._sid)
    except Exception:
        pass
    c.goto(f"https://www.douyin.com/user/{UID}", wait=10)

    info = c.eval_js("""
    (()=>{const h=document.documentElement.innerHTML;
      const g=(re)=>{(h.match(re)||[])[1]||''};
      return JSON.stringify({
        nick: g(/"nickname":"([^"]+)/),
        uid: g(/"unique_id":"([^"]+)/),
        sec: g(/"sec_uid":"([^"]+)/),
        sig: g(/"signature":"([^"]+)/),
        follows: g(/"following_count":(\\d+)/),
        fans: g(/"follower_count":(\\d+)/),
        likes: g(/"total_favorited":(\\d+)/),
        aweme: g(/"aweme_count":(\\d+)/),
        bodyLen: document.body.innerText.length,
        head: document.body.innerText.slice(0,260)
      })})()
    """)
    print("账号信息:", info)

    seen = set()
    stall = 0
    for i in range(MAXROLL):
        r = c.eval_js("""
        (()=>{const a=[...document.querySelectorAll("a[href*='/video/']")];
          return JSON.stringify(a.map(x=>x.getAttribute('href')))})()
        """)
        try:
            links = json.loads(r) if isinstance(r, str) else (r or [])
        except Exception:
            links = []
        before = len(seen)
        for l in links:
            m = re.search(r"/video/(\d+)", l or "")
            if m:
                seen.add(m.group(1))
        gained = len(seen) - before
        pos = c.eval_js(SCROLL_GRID)
        print(f"  滚动{i+1:02d}: 本页{len(links):3d} 新增{gained:3d} 累计{len(seen)} scroll={pos}")
        if gained == 0:
            stall += 1
            if stall >= 4:
                break
        else:
            stall = 0
        time.sleep(1.5)

    vids = sorted(seen)
    json.dump({"sec_uid": UID, "info": info, "videos": vids},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ 抓到 {len(vids)} 个作品 -> {OUT}")
finally:
    c.close()