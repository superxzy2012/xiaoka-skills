#!/usr/bin/env python3
"""B站美客多教程搜索：多关键词 + 年份(2026/2027)过滤 + 去重，输出候选池。"""
import json, time, urllib.parse, sys, os
import http.cookiejar as cj
import urllib.request

CK = "/opt/data/memories/cookies/bilibili_cookies.txt"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36")
OUT = "/opt/data/cache/scratch/mercado_candidates.json"

KEYWORDS = [
    "美客多", "美客多运营", "美客多开店", "美客多教程", "Mercado Libre",
    "MercadoLibre", "美客多跨境", "美客多选品", "美客多物流", "美客多广告",
    "美客多店铺", "美客多订单", "美客多本地化", "melibre", "美客多多站点",
]

def load_cookies():
    c = cj.MozillaCookieJar()
    try:
        c.load(ignore_discard=True, ignore_expires=True)
    except Exception:
        pass
    return c

def search(kw, page=1):
    url = ("https://api.bilibili.com/x/web-interface/search/type"
           f"?search_type=video&keyword={urllib.parse.quote(kw)}&page={page}&order=pubdate")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://search.bilibili.com/"})
    try:
        ck = load_cookies()
        if len(ck) == 0:
            print("!! cookie 加载失败", file=sys.stderr)
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(ck))
        with opener.open(req, timeout=20) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"code": -1, "message": str(e)}

def main():
    seen = {}
    for kw in KEYWORDS:
        for page in (1, 2):
            d = search(kw, page)
            res = (d.get("data") or {}).get("result") or []
            if not res:
                print(f"[{kw} p{page}] 无结果 code={d.get('code')} msg={d.get('message')}")
            for it in res:
                bvid = it.get("bvid")
                if not bvid:
                    continue
                ts = it.get("pubdate") or 0
                import datetime
                y = datetime.datetime.utcfromtimestamp(ts).year
                # 只要 2026 和 2027
                if y not in (2026, 2027):
                    continue
                if bvid in seen:
                    continue
                title = (it.get("title") or "").replace('<em class="keyword">', '').replace("</em>", "")
                seen[bvid] = {
                    "bvid": bvid, "title": title, "year": y,
                    "author": it.get("author"),
                    "mid": it.get("mid"),
                    "play": it.get("play"),
                    "duration": it.get("duration"),
                    "pubdate": ts,
                    "kw": kw,
                }
            print(f"[{kw} p{page}] 累计候选 {len(seen)}")
            time.sleep(2.2)   # 防 -412 限流

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(list(seen.values()), f, ensure_ascii=False, indent=1)
    print(f"\n✅ 共 {len(seen)} 条 2026/2027 候选 -> {OUT}")

if __name__ == "__main__":
    main()