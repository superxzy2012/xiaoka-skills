#!/usr/bin/env python3
"""
学霸妈妈讲AI 作品抓取（修正版）
🔴 修正1：只开 1 个标签循环复用，绝不累积（BOSS 电脑会被多标签卡死）
🔴 修正2：只保留 sec_uid 匹配的作品，主页推荐流混入的他人作品直接跳过
"""
import sys, json, time, urllib.request

CDP = "http://192.168.199.184:9224"
sys.path.insert(0, "/opt/data/memories")
from cdp import CDP

SEC = "MS4wLjABAAAA4ne-HAyUvKW9PkLKE7OOWi6J7R1oVZaJaiWk1-M-vkg"
NICK = "学霸妈妈讲AI"
SRC = "/opt/data/cache/scratch/dyprof_MS4wLjABAAAA.json"
OUT = "/opt/data/cache/scratch/dy_verified.json"

JS = r"""
(()=>{
  const h = document.documentElement.innerHTML;
  const g = re => (h.match(re)||[])[1] || '';
  // 作者 sec：页面里第一个非 self 的 /user/MS4w 链接
  let sec = '';
  for (const a of document.querySelectorAll("a[href*='/user/MS4w']")) {
    const m = (a.getAttribute('href')||'').match(/\/user\/(MS4[A-Za-z0-9_-]+)/);
    if (m && m[1] && a.getAttribute('href') !== '/user/self') { sec = m[1]; break; }
  }
  const t = document.title || '';
  return JSON.stringify({
    sec: sec,
    nick: g(/"nickname":"([^"]+)/),
    desc: g(/"desc":"([^"]{0,110})/),
    dur:  g(/"duration":(\d+)/),
    fav:  g(/"digg_count":(\d+)/),
    date: g(/"create_time":(\d+)/),
    ttl:  t.slice(0, 90)
  })})()
"""


def close_all_douyin():
    """收尾：关掉自己开的所有抖音标签"""
    try:
        with urllib.request.urlopen(f"{CDP}/json/list", timeout=8) as r:
            ts = json.loads(r.read().decode())
        n = 0
        for t in ts:
            if "douyin.com" in t.get("url", ""):
                tid = t["id"]
                try:
                    with urllib.request.urlopen(
                            urllib.request.Request(f"{CDP}/json/close/{tid}"), timeout=5) as r:
                        r.read()
                    n += 1
                except Exception:
                    pass
        print(f"🧹 已关闭 {n} 个抖音标签")
    except Exception as e:
        print("清理异常:", e)


def main():
    ids = json.load(open(SRC))["videos"]
    c = CDP()
    tab = None
    keep, drop, nodata = [], [], []
    try:
        tab = c.new_tab("about:blank")          # 🔴 只开这一个
        print(f"标签已开: {tab[:8]}（全程复用）")
        for i, aid in enumerate(ids, 1):
            rec = None
            for attempt in (1, 2):
                try:
                    c.goto(f"https://www.douyin.com/video/{aid}", wait=10)
                    raw = c.eval_js(JS)
                    if raw:
                        d = json.loads(raw if isinstance(raw, str) else raw)
                        rec = {"id": aid, **d}
                        break
                except Exception as e:
                    print(f"    重试{attempt}: {type(e).__name__}")
                time.sleep(3)
            if not rec:
                nodata.append({"id": aid})
                print(f"[{i}/{len(ids)}] {aid} ⚠️ 未渲染")
                continue
            # 🔴 核心过滤：sec 必须完全等于目标
            if rec.get("sec") == SEC:
                keep.append(rec)
                print(f"[{i}/{len(ids)}] {aid} ✅ {(rec.get('ttl') or '')[:44]}")
            else:
                drop.append(rec)
                print(f"[{i}/{len(ids)}] {aid} ❌ 他人作品 sec={rec.get('sec','?')[-12:]}")
            time.sleep(2.2)
    finally:
        try:
            c.close()
        except Exception:
            pass
        close_all_douyin()
        json.dump({"keep": keep, "drop": drop, "nodata": nodata},
                  open(OUT, "w"), ensure_ascii=False, indent=1)
        print(f"\n✅ 本号 {len(keep)}  剔除 {len(drop)}  无数据 {len(nodata)} -> {OUT}")


if __name__ == "__main__":
    main()