#!/usr/bin/env python
"""记忆自动瘦身器 —— 解决「MEMORY.md 只增不减，几天就满」。

问题（BOSS 2026-10-04 明确提出：不���再过几天处理一次，太麻烦）：
    Hermes 内置记忆是**只增不减**的。hermes memory 只有 setup/status/off/reset，
    没有 archive / prune / compact —— 没有淘汰机制。
    实测从建号到当天，MEMORY.md 已到 97% 上限，且因重复条目反复触顶。

本脚本做什么（每次运行）：
    1. 体检    —— 报告容量、条目数、疑似重复、超期条目
    2. 去重    —— 自动合并/删除内容重复的条目（最常见的溢出原因）
    3. 归档    —— 把「已完成的项目」压成一行指针（细节本就在技能/文件里）
    4. 快照    —— 改之前先备份，可回滚
    5. 通知    —— 腾出多少、动了哪些条目，写进 Obsidian

设计原则：
    · **默认只报告不改**（--apply 才动手）—— 记忆是决策资产，不能被脚本乱删
    · 只删「确定冗余」的：内容重复、已归档项目的历史记述
    · 有疑问的一律保留，宁可满也不能丢关键事实
    · 自带 --selftest —— 没自检的脚本可能一直假 PASS

用法：
    python3 /opt/data/memories/memory_slim.py            # 只体检+报告（默认）
    python3 /opt/data/memories/memory_slim.py --apply    # 真的执行瘦身
    python3 /opt/data/memories/memory_slim.py --selftest # 自检
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime

MEM = "/opt/data/memories/MEMORY.md"
USER = "/opt/data/memories/USER.md"
BAK_DIR = "/opt/data/memories/.memory_backups"
REPORT_DIR = ("/opt/nas/volume2/2-AI/obsidian_vault/"
              "15-小卡工作区/生活服务/记忆体检")
LIMIT = 8000

# ── 归档判定：这些条目说的是「已做完的事」，细节在技能/文件里，不需要留在注入层 ──
ARCHIVE_HINTS = [
    "已完成", "蒸馏《", "实战：", "2026-10-02 发现已有",
]


def now():
    return datetime.now().isoformat(timespec="seconds")


def load():
    if not os.path.exists(MEM):
        return ""
    return open(MEM, encoding="utf-8").read()


def entries(text):
    return [x.strip() for x in text.split("§") if x.strip()]


def norm(s):
    """归一化用于比对：去标点空白、只留中英数。"""
    return re.sub(r"[^\w一-鿿]", "", s.lower())


def find_dups(ents):
    """找内容重复的条目。用「归一化后完全相同」和「前缀高度重叠」两档。"""
    out = []
    # 档1：归一化完全相同
    seen = {}
    for i, e in enumerate(ents):
        k = norm(e)
        if k and k in seen:
            out.append(("完全重复", seen[k], i, e))
        elif k:
            seen[k] = i
    # 档2：同一开头（标题相同但内容不同 = 上一轮 replace 留下的旧版）
    heads = {}
    for i, e in enumerate(ents):
        h = norm(e.split("：")[0].split("（")[0])[:14]
        if len(h) < 6:
            continue
        if h in heads:
            out.append(("标题重复", heads[h], i, e))
        else:
            heads[h] = i
    return out


def find_stale(ents, days=180):
    """找出只由日期戳支撑、且日期已很旧的条目（多半是历史记述）。"""
    today = date.today()
    out = []
    for i, e in enumerate(ents):
        ds = re.findall(r"20\d{2}-\d{2}-\d{2}", e)
        if not ds:
            continue
        try:
            newest = max(date.fromisoformat(d) for d in ds)
        except ValueError:
            continue
        age = (today - newest).days
        # 只是「已完成」类记述且很旧 → 建议归档；环境事实类不算
        if age >= days and any(h in e for h in ARCHIVE_HINTS):
            out.append((i, e, age))
    return out


def backup(tag="auto"):
    os.makedirs(BAK_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dst = f"{BAK_DIR}/MEMORY-{stamp}-{tag}.md"
    shutil.copy2(MEM, dst)
    # 只留最近 20 份，别让备份本身占满磁盘
    olds = sorted(os.listdir(BAK_DIR))[:-20]
    for o in olds:
        os.unlink(os.path.join(BAK_DIR, o))
    return dst


def slim(text, apply=False):
    """返回 (新文本, 变更说明列表)。apply=False 时只演算不落地。"""
    ents = entries(text)
    notes = []

    # 1) 去重：保留信息量更大的那条（更长 = 通常更完整）
    dups = find_dups(ents)
    kill = set()
    for kind, a, b, txt in dups:
        keep, drop = (a, b) if len(ents[a]) >= len(ents[b]) else (b, a)
        kill.add(drop)
        notes.append(f"去重[{kind}] 删「{ents[drop][:26]}…」保留更完整的一条")
    if apply and kill:
        ents = [e for i, e in enumerate(ents) if i not in kill]

    # 2) 归档：历史记述压成一行
    if apply:
        for i, e, age in find_stale(ents):
            head = e.split("：")[0][:18]
            new = f"{head}（已完成，细节见技能/文件）"
            if len(new) < len(e):
                ents[i] = new
                notes.append(f"归档「{e[:26]}…」{len(e)}B→{len(new)}B（{age}天前的完成记述）")

    # 3) 重建
    head = text.split("§")[0].strip() if text.startswith("#") else ""
    body = "\n§\n".join(ents)
    new = f"{head}\n§\n{body}" if head else body
    if not new.endswith("\n"):
        new += "\n"
    return new, notes


def report(text, notes, applied):
    os.makedirs(REPORT_DIR, exist_ok=True)
    p = f"{REPORT_DIR}/{date.today().isoformat()}-记忆体检.md"
    ents = entries(text)
    pct = len(text) / LIMIT * 100
    L = [
        f"# 🧠 记忆体检 {date.today().isoformat()}",
        "",
        f"> {now()} · {'已执行瘦身' if applied else '只体检未改动'}",
        "",
        "## 容量",
        "",
        "| 项 | 值 |",
        "|---|---|",
        f"| 字符 | {len(text)} / {LIMIT} |",
        f"| 占用 | **{pct:.0f}%** |",
        f"| 剩余额度 | {LIMIT - len(text)} |",
        f"| 条目数 | {len(ents)} |",
        f"| 备份 | `{BAK_DIR}`（保留最近20份） |",
        "",
        "## 变更",
        "",
    ]
    if notes:
        for n in notes:
            L.append(f"- {n}")
    else:
        L.append("无需改动 —— 内容无重复、无可归档的过期记述。")
    L.append("")
    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return p


def selftest():
    print("=== 自检 ===")
    # 1) 归一化
    print(f"  {'✅' if norm('A股行情：腾讯 qt.gtimg.cn') == norm('A股行情 腾讯qtgtimgcn') else '❌'} "
          "标点空白归一化生效")
    # 2) 重复检测 —— 必须能抓到「上一轮 replace 留下的旧版」
    dup_src = "造轮子前必先查：A方案。§造轮子前必先查（实测）：A方案，更详细。"
    d = find_dups(entries(dup_src))
    print(f"  {'✅' if d else '❌'} 抓到标题重复（{len(d)} 组）")
    # 3) 不误伤
    clean = "A股行情：腾讯可用。§抖音抓取：API已废弃。"
    d2 = find_dups(entries(clean))
    print(f"  {'✅' if not d2 else '❌'} 不误伤不同条目")
    # 4) 瘦身确实减字符
    src = ("毛选蒸馏已完成：5卷229篇双校验PASS。§"
           "毛选蒸馏已完成：5卷229篇，双校验 PASS（229/229）。§"
           "A股行情：腾讯 qt.gtimg.cn 可用。")
    new, notes = slim(src, apply=True)
    cut = len(src) - len(new)
    print(f"  {'✅' if cut > 0 else '❌'} 瘦身确实减字符（{len(src)}→{len(new)}, −{cut}）")
    print(f"  {'✅' if '腾讯' in new else '❌'} 保留了非重复条目")
    # 5) 过期检测 —— 必须用「真的超过门槛」的日期，否则测试是自欺欺人
    from datetime import timedelta as _td
    stale_src = (f"蒸馏《毛泽东选集》5卷229篇已完成"
                 f"（{(date.today()-_td(days=200)).isoformat()}），双校验器 PASS。")
    fresh_src = (f"蒸馏《毛泽东选集》5卷229篇已完成"
                 f"（{(date.today()-_td(days=10)).isoformat()}），双校验器 PASS。")
    s_hit, f_hit = find_stale(entries(stale_src)), find_stale(entries(fresh_src))
    print(f"  {'✅' if s_hit else '❌'} 抓到200天前的完成记述（应命中，实际{len(s_hit)}）")
    print(f"  {'✅' if not f_hit else '❌'} 10天前的不误伤（不该命中，实际{len(f_hit)}）")
    # 验证门槛真的生效：改 days 参数应改变结果
    a = find_stale(entries(fresh_src), days=5)
    print(f"  {'✅' if a else '❌'} 门槛可调（days=5 时10天前的才命中）")
    # 6) 备份可回滚
    os.makedirs(BAK_DIR, exist_ok=True)
    b = backup("selftest")
    ok = os.path.exists(b)
    print(f"  {'✅' if ok else '❌'} 备份生成成功（{os.path.basename(b)}）")
    os.unlink(b)
    # 7) 空输入不崩
    try:
        slim("", apply=True); report("", [], False)
        print("  ✅ 空输入不崩")
    except Exception as e:
        print(f"  ❌ 空输入崩溃：{e}")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()

    text = load()
    apply = "--apply" in sys.argv
    before = len(text)

    new, notes = slim(text, apply=apply)

    if apply:
        if new != text:
            dst = backup("pre-slim")
            open(MEM, "w", encoding="utf-8").write(new)
            print(f"✅ 已瘦身 {before} → {len(new)} 字符 (−{before-len(new)})")
            print(f"   备份: {dst}")
        else:
            print(f"ℹ️  无需改动（{before} 字符）")
        for n in notes:
            print(f"   · {n}")
    else:
        pct = before / LIMIT * 100
        print(f"=== 记忆体检 {date.today()} ===")
        print(f"  {before}/{LIMIT} 字符（{pct:.0f}%），{len(entries(text))} 条")
        print(f"  可释放: {before - len(new)} 字符")
        if notes:
            print("\n  将执行：")
            for n in notes:
                print(f"   · {n}")
        else:
            print("\n  无需改动")
        print("\n  （这是演练，加 --apply 才真改）")

    p = report(new if apply else text, notes, apply)
    print(f"📄 {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())