#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 知识星球增量入库 v2（CDP 页面内 fetch 路线）
依据共享库 zsxq-import 技能规范：
  - 直连 api.zsxq.com 必被 1059/19301 拦 → 必须在 CDP 的 zsxq 页面上下文 fetch
  - 头必须带 x-version: 2.56.0, x-request-id(随机), Referer, credentials:include
  - 首页 20 条稳定；翻页(end_time)易触发 1059 → 只抓首页
  - 限流 code: 1007 / 1059 / 1004 / 1008
星球：Workbuddy一人公司营(88884585518442) / AI创收私研社(88882458154112)
用法: python3 zsxq_ingest2.py [每星球条数=20] [--no-comments]
"""
import os, re, json, time, random, shutil, datetime, sys
from playwright.sync_api import sync_playwright

CDP = "http://192.168.199.184:9222"
VAULT = "/opt/nas/volume2/2-AI/obsidian_vault"
SCRATCH = "/opt/data/cache/scratch"
ZSXQ_DIR = os.path.join(VAULT, "12-知识星球")
GROUP_URL = "https://wx.zsxq.com/group/{gid}"

PLANETS = [
    ("Workbuddy一人公司营", "88884585518442"),
    ("AI创收私研社", "88882458154112"),
]
THROTTLE = {"1007", "1059", "1004", "1008", "19301"}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def existing_ids(planet):
    root = os.path.join(ZSXQ_DIR, planet)
    ids, n = set(), 0
    if not os.path.isdir(root):
        return ids, 0
    for dp, _, fn in os.walk(root):
        for f in fn:
            if not f.endswith(".md"):
                continue
            n += 1
            m = re.match(r"(\d{15,20})", f)
            if m:
                ids.add(m.group(1))
                continue
            try:
                txt = open(os.path.join(dp, f), encoding="utf-8", errors="ignore").read(4000)
            except Exception:
                continue
            ids.update(re.findall(r'"topic_id"\s*:\s*"?(\d{15,20})', txt))
    return ids, n


def safe(s, maxlen=60):
    s = re.sub(r'[/\\:*?"<>|\r\n\t]', "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:maxlen].strip() or "untitled"


FETCH_JS = """
async ([gid, count]) => {
  const rid = Math.random().toString(36).slice(2) + Date.now();
  const url = `https://api.zsxq.com/v2/groups/${gid}/topics?scope=all&count=${count}&end_time=`;
  const r = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: {
      'x-version': '2.56.0',
      'x-request-id': rid,
      'x-timestamp': String(Date.now()),
      'Referer': 'https://wx.zsxq.com/',
      'Accept': 'application/json, text/plain, */*'
    }
  });
  return await r.text();
}
"""


def fetch_topics(pg, gid, count=20):
    raw = pg.evaluate(FETCH_JS, [gid, count])
    try:
        d = json.loads(raw)
    except Exception as e:
        return {"error": f"JSON 解析失败: {e}", "raw": raw[:300]}
    code = str(d.get("code", ""))
    if code in THROTTLE:
        return {"throttled": code}
    if not d.get("succeeded", False):
        return {"error": f"code={code} {d.get('info','')}"[:200]}
    return {"topics": d.get("resp_data", {}).get("topics", [])}


def topic_text(tp):
    tp = tp.get("topic", tp)
    ttype = tp.get("type", "")
    talk = tp.get("talk") or {}
    owner = (tp.get("owner") or {}).get("name", "未知")
    text = talk.get("text") or tp.get("text") or ""
    # 去 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    create = tp.get("create_time", "")
    tid = str(tp.get("topic_id", ""))
    cmt = tp.get("show_comments") or []
    return {"tid": tid, "type": ttype, "author": owner, "text": text,
            "create": create, "comments": cmt, "raw_len": len(text)}


def build_note(planet, gid, item, url, with_comments=True):
    d = datetime.date.today().isoformat()
    tid = item["tid"] or datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    first = item["text"].split("\n")[0].strip() or item["author"]
    fm = [
        "---",
        f'title: "{safe(first)}"',
        f'zsxq_group_id: "{gid}"',
        f'zsxq_group_name: "{planet}"',
        f'topic_id: "{tid}"',
        f'author: "{item["author"]}"',
        f'topic_type: "{item["type"]}"',
        f'created: "{item["create"]}"',
        f"date: {d}",
        "source: zsxq",
        f"source_url: {url}",
        "tags: [知识星球, 提炼]",
        "added_by: 小卡",
        "---",
        "",
        f"# {safe(first)}",
        "",
        f"> ⭐ {planet} · {item['author']} · {item['type']}",
        "",
        "## 📝 原文",
        "",
        item["text"] or "（无正文）",
    ]
    if with_comments and item["comments"]:
        cl = []
        for c in item["comments"][:6]:
            if isinstance(c, dict):
                who = (c.get("owner") or {}).get("name", "?")
                t = re.sub(r"<[^>]+>", "", c.get("text", ""))
                if t:
                    cl.append(f"**{who}**：{t}")
        if cl:
            fm += ["", "## 💬 精选评论", ""] + cl
    if not item["text"].strip():
        fm += ["", "> ⚠️ 本条无正文（可能为纯图片/视频/附件帖）"]
    fm += ["", "## 🏷️ 标签", f"#知识星球 #{planet}"]
    return f"{tid} - {safe(first)}.md", "\n".join(fm)


def main():
    limit = 20
    with_comments = "--no-comments" not in sys.argv
    for a in sys.argv[1:]:
        if a.isdigit():
            limit = int(a)

    results = []
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(CDP)
        ctx = b.contexts[0]
        pg = ctx.new_page()
        # 先打开星球页建立页面上下文（fetch 必须在 zsxq 页面里跑）
        for planet, gid in PLANETS:
            log(f"\n=== {planet} (group/{gid}) ===")
            ids, n0 = existing_ids(planet)
            log(f"  已有 {n0} 篇，ID {len(ids)} 个")
            url = GROUP_URL.format(gid=gid)
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(9)
                r = fetch_topics(pg, gid, limit)
            except Exception as e:
                log(f"  ❌ {str(e)[:200]}")
                results.append((planet, "error", str(e)[:120]))
                continue

            if r.get("throttled"):
                log(f"  ⚠️ 限流 code={r['throttled']} → 跳过该星球（不硬刷）")
                results.append((planet, "throttled", r["throttled"]))
                time.sleep(20)
                continue
            if r.get("error"):
                log(f"  ❌ {r['error']}")
                results.append((planet, "error", r["error"]))
                continue

            topics = r["topics"]
            log(f"  API 返回 {len(topics)} 条")
            outdir = os.path.join(ZSXQ_DIR, planet, datetime.date.today().strftime("%Y-%m"))
            added = skipped = empty = 0
            os.makedirs(outdir, exist_ok=True)
            for tp in topics:
                item = topic_text(tp)
                if not item["tid"]:
                    empty += 1
                    continue
                if item["tid"] in ids:
                    skipped += 1
                    continue
                if not item["text"].strip() and not item["comments"]:
                    empty += 1
                    continue
                fname, content = build_note(planet, gid, item, url, with_comments)
                tmp = os.path.join(SCRATCH, fname)
                open(tmp, "w", encoding="utf-8").write(content)
                shutil.copy(tmp, os.path.join(outdir, fname))
                ids.add(item["tid"])
                added += 1
                time.sleep(0.3)
            log(f"  ✅ 新增 {added} · 去重跳过 {skipped} · 空/无ID {empty} → {outdir}")
            results.append((planet, "ok", added))
            time.sleep(12)   # 星球间退避，降低限流风险
        pg.close()
        b.close()

    log("\n" + "=" * 55)
    for planet, st, val in results:
        if st == "ok":
            log(f"  ✅ {planet} — 新增 {val} 篇")
        elif st == "throttled":
            log(f"  ⚠️ {planet} — 限流 {val}（已跳过，未硬刷）")
        else:
            log(f"  ❌ {planet} — {val}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
