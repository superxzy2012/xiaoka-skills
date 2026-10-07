#!/usr/bin/env python3
"""从作品页确认作者身份（昵称/抖音号/粉丝数）。"""
import sys, json
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

VID = sys.argv[1] if len(sys.argv) > 1 else "7692853884020182314"
c = CDP()
try:
    c.new_tab("about:blank")
    c.goto(f"https://www.douyin.com/video/{VID}", wait=10)
    js = r"""
    (()=>{
      const h = document.documentElement.innerHTML;
      const g = re => (h.match(re)||[])[1] || '';
      const anchors = [...document.querySelectorAll("a[href*='/user/']")]
        .map(a=>({h:a.getAttribute('href'), t:(a.innerText||'').trim().slice(0,50)}))
        .filter(x=>x.h && x.h.includes('MS4w'));
      return JSON.stringify({
        nick: g(/"nickname":"([^"]+)/),
        uid:  g(/"unique_id":"([^"]+)/),
        fans: g(/"follower_count":(\d+)/),
        likes:g(/"total_favorited":(\d+)/),
        aweme:g(/"aweme_count":(\d+)/),
        sig:  g(/"signature":"([^"]*)/),
        anchors: anchors.slice(0,6),
        head: document.body.innerText.slice(0,200)
      })})()
    """
    print(json.dumps(json.loads(c.eval_js(js)), ensure_ascii=False, indent=1))
finally:
    c.close()