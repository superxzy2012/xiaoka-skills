#!/usr/bin/env python3
"""用验证阶段抓到的真实元数据补全 ingest.py 生成的笔记。"""
import json, os, re, datetime, html

V = "/opt/nas/volume2/2-AI/obsidian_vault/08-抖音视频学习"

d = json.load(open("/opt/data/cache/scratch/dy_verified.json"))
keep = d["keep"]


def fix(aid, ttl):
    """ttl 是验证时抓的 document.title，形如 '标题 - 抖音'"""
    title = re.sub(r"\s*-\s*抖音\s*$", "", ttl or "").strip()
    title = html.unescape(title)
    if not title or title == "抖音":
        return None
    fp = None
    for f in os.listdir(V):
        if f.endswith(f"-{aid}.md"):
            fp = os.path.join(V, f)
            break
    if not fp:
        return None
    t = open(fp, encoding="utf-8").read()
    t = re.sub(r'^title: .*$', f'title: "{title}"', t, count=1, flags=re.M)
    t = re.sub(r'^author: .*$', 'author: "学霸妈妈讲AI"', t, count=1, flags=re.M)
    body = title[:60]
    t = re.sub(r"^# .*$", f"# {body}", t, count=1, flags=re.M)
    t = re.sub(r"^> 🎬 抖音 · 未知 · .*$",
               f"> 🎬 抖音 · 学霸妈妈讲AI", t, count=1, flags=re.M)
    open(fp, "w", encoding="utf-8").write(t)
    return title


ok = miss = 0
for r in keep:
    res = fix(r["id"], r.get("ttl") or "")
    if res:
        ok += 1
    else:
        miss += 1
        print(f"  ⚠️ {r['id']} ttl={(r.get('ttl') or '')[:40]!r} 未匹配到笔记")
print(f"✅ 补全 {ok}/{len(keep)} 条，失败 {miss}")