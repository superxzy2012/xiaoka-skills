#!/usr/bin/env python3
"""探抖音号主页：拿昵称/粉丝数/作品数，并滚动加载全部作品列表。"""
import sys, json, time, re
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

SEC = sys.argv[1] if len(sys.argv) > 1 else "2136352641"
OUT = f"/opt/data/cache/scratch/dy_{SEC}.json"

c = CDP()
try:
    tab = c.new_tab("about:blank")
    print(f"✅ tab={tab}")
    c.goto(f"https://www.douyin.com/user/{SEC}", wait=8)

    info = c.eval_js("""
    (()=>{const q=s=>document.querySelector(s);
      const g=s=>{const e=q(s);return e?e.innerText.trim():''};
      return JSON.stringify({
        title: document.title.slice(0,80),
        url: location.href,
        nickname: g("[data-e2e='user-detail'] [class*='nickname']") || g("h1") || '',
        info: g("[data-e2e='user-info']"),
        bodyLen: document.body.innerText.length
      })})()
    """)
    print("页面信息:", info)

    # 收集作品链接（滚动加载）
    seen = set()
    for i in range(30):
        js = """
        (()=>{const a=[...document.querySelectorAll("a[href*='/video/']")];
          return JSON.stringify(a.map(x=>x.getAttribute('href')))})()
        """
        r = c.eval_js(js)
        try:
            links = json.loads(r) if isinstance(r, str) else (r or [])
        except Exception:
            links = []
        before = len(seen)
        for l in links:
            m = re.search(r"/video/(\d+)", l or "")
            if m:
                seen.add(m.group(1))
        print(f"  滚动{i+1}: 本页{len(links)} 累计{len(seen)}")
        if len(seen) == before and i > 3:
            break
        c.eval_js("window.scrollBy(0, 3000)")
        time.sleep(1.6)

    vids = sorted(seen)
    json.dump({"sec_id": SEC, "info": info, "videos": vids},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print(f"\n✅ 抓到 {len(vids)} 个作品 -> {OUT}")
    print("   样例:", vids[:5])
finally:
    c.close()