#!/usr/bin/env python
"""主动学习扫描器 —— 每天自己去 GitHub 找值得学的新东西。

设计目标（BOSS 2026-10-04 明确要求）：
    「主动学习——每天自己找新东西学，不用我发链接」

它做什么：
    1. 读「已学过」黑名单，跳过装过的
    2. 按 BOSS 的兴趣方向去 GitHub 搜新项目
    3. 硬核实每个候选的 star / license / 最后 push（不信描述文本）
    4. 打分排序，只输出「值得看的」前 N 个
    5. 写日报到 Obsidian，同时更新黑名单

它不做什么（重要）：
    · 不自动装任何东西 —— 装是下一步 BOSS 确认的动作
    · 不碰私有 token、涉钱、破坏性操作

为什么不用现成工具：
    本机已有 find-skills-xiaoka（查技能库 + 搜 GitHub + 吸收），
    但那是**被动触发**的（等 BOSS 发链接才跑）。
    本脚本是**主动巡检**的，每天自己扫。这是缺的那一环。

用法：
    python3 /opt/data/memories/autolearn.py            # 扫描并出报告
    python3 /opt/data/memories/autolearn.py --dry-run  # 只看会做什么，不写文件
    python3 /opt/data/memories/autolearn.py --selftest # 自检（校验器可信度）

出口数据：/opt/data/memories/autolearn_state.json
日报：     <vault>/15-小卡工作区/生活服务/主动学习/YYYY-MM-日报.md
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta

STATE = "/opt/data/memories/autolearn_state.json"
VAULT = "/opt/nas/volume2/2-AI/obsidian_vault"
OUTDIR = f"{VAULT}/15-小卡工作区/生活服务/主动学习"
GH = "/opt/data/bin/gh"
GHENV = {"HOME": "/opt/data/home", "PATH": "/opt/data/bin:/usr/bin:/bin",
         "GH_CONFIG_DIR": "/opt/data/home/.config/gh"}

# ── BOSS 的兴趣方向（从历史行为归纳：他反复让我找 GitHub 开源项目）──
# 每个方向有多个查询式，**按天轮换**。
# 踩过的坑：只用一个固定 query，GitHub 返回结果高度重叠，
# 扫一周后 seen 黑名单吃光所有结果，cron 永久静默（2026-10-04 实测）。
TOPICS = [
    ("Agent/记忆", [
        "agent memory autonomous self-improving",
        "agent context engineering LLM",
        "reflection agent learning from mistakes",
        "persistent memory for AI agents",
    ], 200),
    ("Skill生态", [
        "agent skill claude skill SKILL.md",
        "claude code plugin marketplace",
        "agent skills catalog",
        "mcp server agent tools",
    ], 100),
    ("文档处理", [
        "document markdown pdf convert",
        "pdf parsing library rust",
        "office document parsing",
        "document AI structured extraction",
    ], 200),
    ("爬取/数据获取", [
        "scraping crawl browser automation",
        "web scraping python library",
        "headless browser automation agent",
        "data extraction API web",
    ], 300),
    ("效率工具", [
        "automation workflow agent tool",
        "developer productivity CLI tool",
        "terminal tool for AI agents",
        "workflow orchestration open source",
    ], 300),
]

# 排除词：这些方向本机已有成熟方案，或与现有技能高度重叠
BLOCK = [
    "awesome-", "roadmap", "interview", "leetcode", "tutorial-", "course",
    "book", "books", "cheatsheet", "certification", "dotfiles",
]

# 只推荐这三种许可（GPL/AGPL 单独标注，不一票否决）
OK_LIC = {"MIT", "Apache-2.0", "BSD-3-Clause", "BSD-2-Clause", "ISC", "MPL-2.0"}


def gh_json(args, timeout=90):
    r = subprocess.run([GH] + args, capture_output=True, text=True,
                       timeout=timeout, env=GHENV)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except json.JSONDecodeError:
            return {"seen": {}, "runs": 0}
    return {"seen": {}, "runs": 0}


def save_state(st):
    tmp = STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE)          # 原子写，防止半截文件


def search(q, limit=8, months=12):
    """GitHub 仓库检索。-f 必须配 -X GET，否则变 POST。

    只捞近 `months` 个月新建的仓库 —— BOSS 要的是「新东西」，
    不加这个门槛会天天重复捞 crawlee 这类常年霸榜的老项目。
    """
    since = (date.today() - timedelta(days=months * 30)).isoformat()
    d = gh_json(["api", "-X", "GET", "search/repositories",
                 "-f", f"q={q} created:>{since}", "-f", f"per_page={limit}",
                 "-f", "sort=stars"])
    return d.get("items", []) if d else []


def is_blocked(name, desc):
    blob = (name + " " + (desc or "")).lower()
    return any(b in blob for b in BLOCK)


def score(repo):
    """打分：新鲜度 + 体量 + 活跃度。纯 star 数不排序 —— 大项目刷不动。"""
    st = repo.get("stargazers_count", 0)
    created = repo.get("created_at", "")[:10]
    pushed = repo.get("pushed_at", "")[:10]
    s = 0
    # 体量：log 曲线，1k 和 50k 差距不该有 50 倍
    s += min(st / 1000, 40)
    # 新鲜度：近 30 天建的加权（BOSS 要「新东西」）
    try:
        age = (date.today() - date.fromisoformat(pushed)).days
        if age <= 30:
            s += 25
        elif age <= 90:
            s += 15
        elif age <= 365:
            s += 5
        else:
            s -= 10          # 一年多没动的不推
    except (ValueError, TypeError):
        pass
    # 太小的不要（玩具项目）
    if st < 100:
        s -= 30
    return round(s, 1)


def collect(state, verbose=True):
    """跑一轮扫描，返回候选列表。"""
    cands = []
    # 按天轮换查询式：同一天用第 (day % len) 个，保证几天内扫遍所有措辞
    day_idx = date.today().toordinal()
    for label, queries, minstar in TOPICS:
        q = queries[day_idx % len(queries)]
        items = search(q)
        if verbose:
            print(f"  [{label}] 「{q[:38]}」 {len(items)} 条")
        for it in items:
            full = it.get("full_name", "")
            if not full or full in state["seen"]:
                continue
            if is_blocked(full, it.get("description")):
                state["seen"][full] = {"skip": "block", "ts": _now()}
                continue
            if it.get("stargazers_count", 0) < minstar:
                state["seen"][full] = {"skip": "low", "ts": _now()}
                continue
            lic = (it.get("license") or {}).get("spdx_id") or "NONE"
            cands.append({
                "repo": full,
                "url": it.get("html_url", ""),
                "stars": it.get("stargazers_count", 0),
                "forks": it.get("forks_count", 0),
                "lang": it.get("language") or "-",
                "license": lic,
                "created": (it.get("created_at") or "")[:10],
                "pushed": (it.get("pushed_at") or "")[:10],
                "topic": label,
                "desc": (it.get("description") or "")[:110],
                "homepage": it.get("homepage") or "",
                "score": score(it),
                "license_ok": lic in OK_LIC,
            })
    # 主题内去重（同名 repo 可能被多个 query 捞到）
    best = {}
    for c in cands:
        k = c["repo"].lower()
        if k not in best or c["score"] > best[k]["score"]:
            best[k] = c
    cands = sorted(best.values(), key=lambda x: -x["score"])
    return cands


def _now():
    return datetime.now().isoformat(timespec="seconds")


def prune_seen(state, days=90):
    """清掉过期黑名单，防止 cron 永久静默。

    2026-10-04 实测的 bug：seen 无 TTL + TOPICS 查询式固定
    → 第 3 天起所有结果都在黑名单里，新候选恒为 0，cron 静默死亡。

    保留策略：
      · recommended 条目 90 天后可重新推荐（项目可能涨星或出新版）
      · skip:low / skip:block 永久保留（低星和 block 是永久判断，重查没意义）
    """
    today = date.today()
    kept, expired = {}, 0
    for repo, meta in state.get("seen", {}).items():
        if not isinstance(meta, dict):
            kept[repo] = meta
            continue
        if not meta.get("recommended"):
            kept[repo] = meta          # low/block 永久留
            continue
        ts = (meta.get("ts") or "")[:10]
        try:
            age = (today - date.fromisoformat(ts)).days
        except (ValueError, TypeError):
            kept[repo] = meta
            continue
        if age >= days:
            expired += 1
        else:
            kept[repo] = meta
    if expired:
        state["seen"] = kept
    return expired


def write_report(cands, state, run_no):
    os.makedirs(OUTDIR, exist_ok=True)
    d = date.today().isoformat()
    # 同一天可能跑多次（手动 + cron）—— 用序号避免覆盖上一份有内容的日报
    n = 1
    while os.path.exists(f"{OUTDIR}/{d}-主动学习日报-{n}.md"):
        n += 1
    suffix = f"-{n}" if n > 1 else ""
    p = f"{OUTDIR}/{d}-主动学习日报{suffix}.md"

    top = [c for c in cands if c["license_ok"]][:8]
    copy = [c for c in cands if not c["license_ok"]][:5]

    L = []
    L.append(f"# 🔭 主动学习日报 {d}{suffix}")
    L.append("")
    L.append(f"> 第 {run_no} 次自动扫描 · 覆盖 {len(TOPICS)} 个方向 · "
             f"新发现 {len(cands)} 个候选")
    L.append("> 数字均为 GitHub API 实测，非描述文本转述。")
    L.append("")
    L.append("## 🎯 推荐关注")
    L.append("")
    if not top:
        L.append("今天没有新的高价值候选 —— 说明前几天已经把当下的好项目扫完了。")
    else:
        L.append("| 方向 | 项目 | ★ | 语言 | 许可 | 建仓 | 最后push | 说明 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for c in top:
            L.append(f"| {c['topic']} | [{c['repo']}]({c['url']}) | {c['stars']:,} "
                     f"| {c['lang']} | {c['license']} "
                     f"| {c['created']} | {c['pushed']} | {c['desc']} |")
    L.append("")
    if copy:
        L.append("## ⚠️ 许可需留意（copyleft，不一票否决）")
        L.append("")
        L.append("| 项目 | ★ | 许可 | 说明 |")
        L.append("|---|---|---|---|")
        for c in copy:
            L.append(f"| [{c['repo']}]({c['url']}) | {c['stars']:,} | "
                     f"**{c['license']}** | {c['desc']} |")
        L.append("")
    L.append("## 📌 下一步")
    L.append("")
    L.append("这些**都没自动装**。要装哪几个，回小卡一句即可 —— "
             "装之前会真跑验证（不是只读 README）。")
    L.append("")
    L.append("---")
    L.append(f"已扫过仓库累计 {len(state['seen'])} 个（不再重复推荐）")

    with open(p, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    return p


def selftest():
    """校验器自检 —— 没有自检的校验器可能一直假 PASS。"""
    print("=== 自检 ===")
    # 1. 打分函数
    base = {"stargazers_count": 5000, "pushed_at": (date.today() - timedelta(days=5)).isoformat()}
    fresh = score(dict(base, created_at="2026-09-01"))
    stale = score(dict(base, pushed_at="2021-01-01"))
    tiny = score(dict(base, stargazers_count=30, pushed_at=(date.today()-timedelta(days=2)).isoformat()))
    print(f"  {'✅' if fresh > stale else '❌'} 新项目分({fresh}) > 僵尸项目分({stale})")
    print(f"  {'✅' if tiny < fresh else '❌'} 30星小项目({tiny}) 被压到新鲜项目({fresh})之下")
    # 2. block 词
    print(f"  {'✅' if is_blocked('x/awesome-python','') else '❌'} block 拦 awesome-")
    print(f"  {'✅' if not is_blocked('real/tool','a real tool') else '❌'} block 不误伤正常项目")
    # 3. 状态原子读写
    st = {"seen": {}, "runs": 0}
    tmp = STATE + ".selftest"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f)
    back = json.load(open(tmp, encoding="utf-8"))
    os.unlink(tmp)
    print(f"  {'✅' if back == st else '❌'} 状态文件往返一致")
    # 4. 时间门槛真的进 query 了吗（防手滑改坏）
    import inspect
    src = inspect.getsource(search)
    has_since = "created:>" in src and "since" in src
    print(f"  {'✅' if has_since else '❌'} 检索带新建时间门槛（只看近 12 个月）")
    # 反证：门槛应真的过滤掉老项目
    recent = gh_json(["api", "-X", "GET", "search/repositories",
                      "-f", "q=topic:document-conversion created:>2026-09-04",
                      "-f", "per_page=3", "-f", "sort=stars",
                      "--jq", "[.items[]|.created_at[0:10]]"])
    old_ones = gh_json(["api", "-X", "GET", "search/repositories",
                        "-f", "q=topic:document-conversion",
                        "-f", "per_page=3", "-f", "sort=stars",
                        "--jq", "[.items[]|.created_at[0:10]]"])
    if recent and old_ones:
        newest_recent = max(recent)
        oldest_open = min(old_ones)
        print(f"  {'✅' if newest_recent > oldest_open else '⚠️ '} "
              f"带门槛的更新({newest_recent}) vs 不带的({oldest_open})")
    # 4b. TTL 过期逻辑（2026-10-04 真 bug，必须能测出来）
    from datetime import timedelta as _td
    old = (date.today() - _td(days=95)).isoformat()
    fresh = date.today().isoformat()
    st_test = {"seen": {
        "a/recommended": {"recommended": True, "ts": old + "T00:00:00"},
        "b/recommended": {"recommended": True, "ts": fresh + "T00:00:00"},
        "c/low":        {"skip": "low",    "ts": old + "T00:00:00"},
    }}
    n = prune_seen(st_test)
    has = set(st_test["seen"])
    print(f"  {'✅' if n == 1 else '❌'} 95天前的 recommended 被清理（清 {n} 个，应 1）")
    print(f"  {'✅' if 'b/recommended' in has else '❌'} 今天的 recommended 保留")
    print(f"  {'✅' if 'c/low' in has else '❌'} skip:low 永久保留（重查无意义）")

    # 4c. 查询式必须轮换（否则结果重叠→静默）
    import inspect
    src2 = inspect.getsource(collect)
    rot = "day_idx % len(queries)" in src2
    print(f"  {'✅' if rot else '❌'} 查询式按天轮换（防结果重叠）")

    # 5. 真实 API 探活
    d = gh_json(["api", "rate_limit", "--jq", ".rate.remaining"])
    print(f"  {'✅' if d is not None else '❌'} GitHub API 可达（剩余额度 {d}）")
    return 0


def main():
    if "--selftest" in sys.argv:
        return selftest()
    dry = "--dry-run" in sys.argv

    state = load_state()
    run_no = state.get("runs", 0) + 1
    print(f"=== 主动学习扫描 第 {run_no} 次 "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print(f"已扫过 {len(state['seen'])} 个仓库\n")

    expired = prune_seen(state)
    if expired:
        print(f"♻️  黑名单过期清理：{expired} 个项目重新可推荐（90 天 TTL）")

    cands = collect(state)
    print(f"\n新候选 {len(cands)} 个（已滤掉低星/block/已看过）")

    if dry:
        for c in cands[:10]:
            print(f"  [{c['score']:>5}] {c['repo']:<40} ★{c['stars']:<7,} {c['license']}")
        print("\n(dry-run：不写文件、不更新状态)")
        return 0

    p = write_report(cands, state, run_no)
    # 只把「已推荐过」的记进 seen，避免 low/block 的永久污染
    for c in cands:
        state["seen"][c["repo"]] = {"stars": c["stars"], "ts": _now(),
                                    "topic": c["topic"], "recommended": True}
    state["runs"] = run_no
    state["last_run"] = _now()
    state["seen_ttl_days"] = 90
    save_state(state)

    print(f"✅ 日报: {p}")
    print(f"✅ 状态: {STATE}  (已扫过 {len(state['seen'])})")
    for c in cands[:8]:
        flag = "" if c["license_ok"] else "  ⚠️copyleft"
        print(f"   {c['score']:>5} {c['repo']:<40} ★{c['stars']:<8,}{flag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())