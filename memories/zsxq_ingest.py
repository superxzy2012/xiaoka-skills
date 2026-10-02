#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 知识星球增量入库（CDP 路线，避开 API 401 / 限流）
星球：Workbuddy一人公司营(88884585518442) / AI创收私研社(88882458154112)
策略：主贴 + 精选评论；按 topic_id 去重；遇限流立即退避停止
"""
import os, re, json, time, shutil, datetime, sys
from playwright.sync_api import sync_playwright

CDP = "http://192.168.199.184:9222"
VAULT = "/opt/nas/volume2/2-AI/obsidian_vault"
SCRATCH = "/opt/data/cache/scratch"
ZSXQ_DIR = os.path.join(VAULT, "12-知识星球")

PLANETS = [
    {"name": "Workbuddy一人公司营", "gid": "88884585518442"},
    {"name": "AI创收私研社", "gid": "88882458154112"},
]

# 限流信号
THROTTLE_CODES = {"1007", "1059", "1004", "1008"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def existing_ids(planet):
    """收集该星球目录已有的 topic_id"""
    root = os.path.join(ZSXQ_DIR, planet)
    ids = set()
    if not os.path.isdir(root):
        return ids, 0
    n = 0
    for dp, _, fn in os.walk(root):
        for f in fn:
            if not f.endswith(".md"):
                continue
            n += 1
            m = re.match(r"(\d{15,20})", f)
            if m:
                ids.add(m.group(1))
                continue
            fp = os.path.join(dp, f)
            try:
                txt = open(fp, encoding="utf-8", errors="ignore").read(4000)
            except Exception:
                continue
            for x in re.findall(r'"topic_id"\s*:\s*"?(\d{15,20})', txt):
                ids.add(x)
            for x in re.findall(r"\b(\d{17,20})\b", txt[:1500]):
                ids.add(x)
    return ids, n


def safe(s, maxlen=70):
    s = re.sub(r'[/\\:*?"<>|\r\n\t]', "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].strip() or "untitled"


def scrape_planet(pg, ctx, planet, gid, limit=20, with_comments=True):
    """打开星球页，滚 N 屏，采集主贴 + 精选评论"""
    url = f"https://wx.zsxq.com/group/{gid}"
    pg.goto(url, wait_until="domcontentloaded", timeout=60000)
    time.sleep(9)
    pg.set_viewport_size({"width": 1440, "height": 1200})
    time.sleep(3)

    t = pg.inner_text("body")
    # 限流检测
    for code in THROTTLE_CODES:
        if f'"code":{code}' in t or f"code {code}" in t.lower():
            return {"throttled": code, "items": []}

    collected = {}
    for screen in range(6):
        items = pg.evaluate("""() => {
          const out = [];
          document.querySelectorAll('div').forEach(e => {
            const tx = (e.innerText || '').trim();
            if (!tx || tx.length < 25 || tx.length > 2500) return;
            // 主贴：含日期时间
            const dm = tx.match(/(20\\d\\d-\\d\\d-\\d\\d\\s+\\d\\d:\\d\\d)/);
            if (!dm) return;
            // 找 topic_id 线索（DOM 里的 data 属性 / 链接）
            let tid = e.getAttribute('data-topic-id') || '';
            if (!tid) {
              const a = e.querySelector('a[href*="topic"],a[href*="/d/"]');
              if (a) { const m = a.href.match(/(\\d{15,20})/); if (m) tid = m[1]; }
            }
            out.push({tid: tid, ts: dm[1], text: tx});
          });
          return out;
        }""")
        for it in items:
            key = it["tid"] or hash(it["text"][:120])
            if key not in collected:
                collected[key] = it
        # 滚屏加载更多
        pg.mouse.wheel(0, 3200)
        time.sleep(3.5)
        if len(collected) >= limit * 3:
            break

    # 精选评论
    comments = {}
    if with_comments and collected:
        for key, it in list(collected.items())[:8]:
            try:
                pg.evaluate("""(t) => {
                  const els = Array.from(document.querySelectorAll('div'));
                  const hit = els.find(e => (e.innerText||'').includes(t.text.slice(30, 80)));
                  if (hit) {
                    const btn = Array.from(hit.querySelectorAll('span,div'))
                      .find(x => /展开|查看.{0,4}评论|\\d+条评论/.test(x.innerText||''));
                    if (btn) btn.click();
                  }
                }""", it)
                time.sleep(1.6)
                c = pg.evaluate("""() => {
                  const out=[];
                  document.querySelectorAll('[class*="comment"],[class*="reply"]').forEach(e=>{
                    const tx=(e.innerText||'').trim();
                    if(tx && tx.length>6) out.push(tx.slice(0,300));
                  });
                  return Array.from(new Set(out)).slice(0,8);
                }""")
                if c:
                    comments[key] = c
            except Exception:
                pass

    return {"throttled": None, "items": list(collected.values()), "comments": comments}


def build_note(planet, gid, it, comments, url):
    d = datetime.date.today().isoformat()
    tid = it["tid"] or datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    lines = it["text"]
    # 拆作者行
    author = lines.split("\n")[0].strip()[:40]
    fm = [
        "---",
        f'title: "{safe(lines.split(chr(10))[0], 60)}"',
        f'zsxq_group: "{gid}"',
        f'zsxq_group_name: "{planet}"',
        f'topic_id: "{tid}"',
        f'author: "{author}"',
        f"created: {it['ts']}",
        f"date: {d}",
        f"source: zsxq",
        f"source_url: {url}",
        "tags: [知识星球, 提炼]",
        "added_by: 小卡",
        "---",
        "",
        f"# {safe(lines.split(chr(10))[0], 60)}",
        "",
        f"> ⭐ {planet} · {author} · {it['ts']}",
        "",
        "## 📝 原文",
        "",
        lines,
    ]
    if comments:
        lines_c = []
        for c in comments:
            lines_c.append(f"- {c}")
        lines_c = "\n".join(lines_c)
        if lines_c.strip():
            fm += ["", "## 💬 精选评论", "", lines_c]
    fm += ["", "## 🏷️ 标签", f"#知识星球 #{planet}"]
    return f"{tid} - {safe(lines.split(chr(10))[0], 60)}.md", "\n".join(fm)


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    results = []
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        for pl in PLANETS:
            name, gid = pl["name"], pl["gid"]
            log(f"\n=== {name} (group/{gid}) ===")
            ids, n0 = existing_ids(name)
            log(f"  已有 {n0} 篇，提取 ID {len(ids)} 个")
            pg = ctx.new_page()
            try:
                r = scrape_planet(pg, ctx, name, gid, limit)
                if r["throttled"]:
                    log(f"  ⚠️ 限流 code={r['throttled']} → 立即停止该星球")
                    results.append({"planet": name, "throttled": r["throttled"], "new": 0})
                    pg.close()
                    continue
                items, comments = r["items"], r.get("comments", {})
                log(f"  抓到 {len(items)} 条候选")

                added, skipped = 0, 0
                outdir = os.path.join(ZSXQ_DIR, name, d if False else datetime.date.today().strftime("%Y-%m"))
                for it in items:
                    tid = it["tid"]
                    if tid and tid in ids:
                        skipped += 1
                        continue
                    fname, content = build_note(name, gid, it, comments.get(tid or hash(it["text"][:120]), []),
                                                f"https://wx.zsxq.com/group/{gid}")
                    os.makedirs(outdir, exist_ok=True)
                    tmp = os.path.join(SCRATCH, fname)
                    open(tmp, "w", encoding="utf-8").write(content)
                    shutil.copy(tmp, os.path.join(outdir, fname))
                    if tid:
                        ids.add(tid)
                    added += 1
                    time.sleep(0.4)
                log(f"  ✅ 新增 {added} 篇（去重跳过 {skipped}）→ {outdir}")
                results.append({"planet": name, "new": added, "skipped": skipped, "dir": outdir})
            except Exception as e:
                log(f"  ❌ {name}: {str(e)[:200]}")
                results.append({"planet": name, "error": str(e)[:200]})
            finally:
                pg.close()
        b.close()

    log("\n" + "=" * 55)
    for r in results:
        if r.get("error"):
            log(f"  ❌ {r['planet']} — {r['error']}")
        elif r.get("throttled"):
            log(f"  ⚠️ {r['planet']} — 限流 {r['throttled']}")
        else:
            log(f"  ✅ {r['planet']} — 新增 {r['new']} 篇")
    return 0


if __name__ == "__main__":
    sys.exit(main())
