#!/usr/bin/env python3
"""抖音笔记自动核查器 —— 入库时对视频声称的数据做回源比对。

背景（小卡 2026-10-03 实战）：本会话 7 条抖音笔记里 3 条有数字硬伤：
  · 来信AI工具箱 —— 声称的下载量排名全错
  · 洛雪音乐 Docker —— 声称「官方有 Docker」，实际官方无
  · HowToLiveBetter —— 声称 601 条 / 25K star，实际 654 条 / 36,360 star
数字类说法肉眼无法判断对错，必须回源。

能力：
  1. extract_numbers —— 从笔记抽出所有「数字+单位」声称（star/条目/价格/时长等）
  2. verify_repo —— 调 GitHub API 拿仓库真实值，与笔记里的声称比对
  3. verify_license —— 回源判定许可证（复用 resolve_license.py，自检过12/12）
  4. scan —— 扫描目录里所有笔记，标出可疑项

用法：
    factcheck.py <笔记.md> [<笔记.md> ...]     # 核查指定笔记
    factcheck.py --scan <目录>                  # 扫描整个目录
    factcheck.py --selftest                     # 自检（必须有反例）
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

GH = "/opt/data/bin/gh"
ENV = {**os.environ, "HOME": "/opt/data/home", "GH_CONFIG_DIR": "/opt/data/home/.config/gh"}
RESOLVE = "/opt/data/skills/find-skills-xiaoka/scripts/resolve_license.py"
PY = "/opt/data/.venv-browser/bin/python"

# ────────────────────────────────────────────────────────── 数字声称抽取

# 单位 → (字段名, 说明)。只收可回源的量纲。
# 顺序即优先级：先匹配带 K/万 的简写，再匹配普通数字。
# 反例（自检抓到）：「25K 的 star」中间隔了「的」，裸正则 `25K\s*star` 匹配不到。
# 故 K 后缀一律允许中间插入少量修饰字。
_K = r"(?:[kK]|千)"
UNITS = [
    (rf"([\d.]+)\s*{_K}\s*[个]?\s*(?:的\s*)?(?:star|Star|STAR|⭐|星)", "stars_k", "star 数(千)"),
    (r"([\d,]+)\s*[kK]\s*[个]?\s*(?:的\s*)?(?:star|Star|⭐|星)", "stars_k", "star 数(千)"),
    (r"([\d,]+)\s*(?:个)?\s*[kK]?\s*(?:的\s*)?(?:star|Star|STAR|⭐|星)", "stars", "star 数"),
    # 裸 K+star：「30K star」「36k stars」——反例：前一条要求 star 前有分隔符，抓不到这种紧贴写法
    (r"([\d,]+)\s*[kK]\s*(?:的\s*)?(?:star|Star|STAR|⭐|星)s?\b", "stars_k", "star 数(千)"),
    (r"([\d,]+)\s*[条項项]\s*(?:建议|条目|内容|技巧|经验)", "entries", "条目数"),
    (r"([\d,]+)\s*个\s*主题", "topics", "主题数"),
    (r"([\d,]+)\s*个\s*(?:skill|技能)", "skills", "技能数"),
    (rf"([\d.]+)\s*{_K}\s*(?:的\s*)?(?:下载|次下载|下载量)", "downloads_k", "下载量(千)"),
    (r"([\d,]+)\s*[kK]\s*(?:的\s*)?(?:下载量|次下载|下载)", "downloads_k", "下载量(千)"),
    # 延迟：数字+秒，且后文 12 字内出现 判定/决策/响应/推理/加载/启动
    (r"([\d.]+)\s*(?:秒|s)(?=[^。！!，,\n]{0,12}(?:判定|决策|响应|推理|加载|启动|识别))", "latency_s", "延迟(秒)"),
    (r"\$\s*([\d.]+)", "price_usd", "价格(美元)"),
]

REPO_RE = re.compile(r"`([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)`"
                     r"|https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)"
                     r"(?=[^\w.-]|$)")
# 裸文本形式（不带反引号/URL）：owner/repo。必须带 lookaround 防止匹配普通文本里的斜杠。
# 排除路径误伤：/opt/data、./foo 这类左侧含 / . 且不以字母数字开头的片段。
REPO_BARE = re.compile(r"(?<![\w./-])([A-Za-z][\w.-]{0,38}/[A-Za-z][\w.-]{0,60})(?![\w./-])")


def extract_numbers(text: str) -> dict:
    """从笔记正文抽取数字声称。返回 {字段: (值, 原句, 说明)}。

    字段名归一化：所有千/K 后缀的 star 与下载量都折算成实际数量，
    统一存到stars / downloads。这样 set(字段) 的比对才有意义，
    也让 compare() 不必关心来源写法。
    """
    raw = {}
    for pat, key, desc in UNITS:
        for m in re.finditer(pat, text):
            v = m.group(1).replace(",", "")
            try:
                val = float(v)
            except ValueError:
                continue
            if key.endswith("_k"):
                val *= 1000
            s = text.rfind("\n", 0, m.start()) + 1
            e = text.find("\n", m.end())
            line = text[s:e if e > 0 else m.end() + 60].strip()[:90]
            raw.setdefault(key, (val, line, desc))

    # 归一化：stars_k → stars（取较大/较晚出现的那个为准），downloads_k 同理
    out = {}
    for key, (val, line, desc) in raw.items():
        base = key[:-2] if key.endswith("_k") else key
        if base in out and out[base][0] != val:
            # 同时出现 25K 和 30K 这类，保留非_k 精确写法
            if key.endswith("_k") and not out[base][3]:
                out[base] = (val, line, desc, key.endswith("_k"))
        else:
            out.setdefault(base, (val, line, desc, key.endswith("_k")))
    return out


def extract_repos(text: str) -> list[str]:
    seen = []
    for m in REPO_RE.finditer(text):
        r = m.group(1) or m.group(2)
        r = r.rstrip(".,)")
        if r.count("/") == 1 and not r.startswith(("http", "www")) and r not in seen:
            seen.append(r)
    for m in REPO_BARE.finditer(text):
        r = m.group(1).rstrip(".,)")
        if r not in seen:
            seen.append(r)
    return [r for r in seen if not _is_fake_repo(r)]


# 裸文本斜杠会误抽到这些形态 —— 反例（实战抓出）：
#   cloud/turbo        ← 转写引擎名
#   FACT/ESTIMATE      ← 本机技能里的概念标签
#   raw.githubusercontent.com/main ← 域名路径
#   15-小卡工作区/开源源码   ← 中文本地路径
FAKE_EXACT = {"cloud/turbo", "FACT/ESTIMATE", "TBD/NA", "N/A",
              "owner/repo", "owner", "repo", "your/repo", "your-username/repo",
              "memories/factcheck.py", "skills/factcheck.py"}
FAKE_PREFIX = ("raw.githubusercontent.com", "githubusercontent.com",
               "localhost", "127.0.0.1", "example.com",
               "opt/", "home/", "var/", "usr/", "tmp/")
# 笔记里常出现的「文件路径形态」—— 右侧带已知脚本/配置扩展名的一律不是仓库
FILE_SUFFIX = (".py", ".sh", ".md", ".json", ".yml", ".yaml", ".txt", ".js",
               ".ts", ".html", ".css", ".csv", ".log", ".ini", ".cfg", ".toml")


def _is_fake_repo(r: str) -> bool:
    if r in FAKE_EXACT:
        return True
    if any(r.startswith(p) for p in FAKE_PREFIX):
        return True
    # 左侧含中文 → 是本地目录不是 GitHub owner
    if re.search(r"[\u4e00-\u9fff]", r):
        return True
    # 右侧是脚本/配置扩展名 → 是文件路径不是仓库
    if r.lower().endswith(FILE_SUFFIX):
        return True
    return False


# ────────────────────────────────────────────────────────── 回源核实

def gh_api(path: str, timeout: int = 40):
    r = subprocess.run([GH, "api", path], capture_output=True, text=True, env=ENV, timeout=timeout)
    try:
        return json.loads(r.stdout)
    except Exception:
        return None


def verify_repo(repo: str) -> dict:
    """拿仓库真实数据 + 许可证判定。"""
    d = gh_api(f"repos/{repo}")
    if not d or d.get("message"):
        return {"repo": repo, "ok": False, "error": (d or {}).get("message", "查不到")}
    out = {"repo": repo, "ok": True,
           "stars": d.get("stargazers_count"),
           "forks": d.get("forks_count"),
           "license": (d.get("license") or {}).get("spdx_id"),
           "created": (d.get("created_at") or "")[:10],
           "pushed": (d.get("pushed_at") or "")[:10],
           "archived": d.get("archived"), "desc": d.get("description")}
    # 许可证回源（跑已自检的脚本，不自己重实现）
    r = subprocess.run([PY, RESOLVE, repo], capture_output=True, text=True, timeout=200)
    out["license_resolved"] = None
    for ln in r.stdout.split("\n"):
        if "回源判定" in ln:
            out["license_resolved"] = ln.split(":", 1)[1].split("(")[0].strip()
    return out


def resolve_license_batch(repos: list[str]) -> dict:
    """一次跑 resolve_license.py 解析多个仓库的许可证。"""
    if not repos:
        return {}
    r = subprocess.run([PY, RESOLVE] + repos, capture_output=True, text=True, timeout=400)
    out, cur = {}, None
    for ln in r.stdout.split("\n"):
        m = re.match(r"^(\S+/\S+)\s+★", ln)
        if m:
            cur = m.group(1)
            out[cur] = {}
        elif cur and "回源判定" in ln:
            out[cur]["resolved"] = ln.split(":", 1)[1].split("(")[0].strip()
        elif cur and "冲突" in ln:
            out[cur]["conflict"] = ln.split(":", 1)[1].strip()
    return out


# ────────────────────────────────────────────────────────── 比对判定

TOL = 0.06  # 6% 容差（star 会实时涨，笔记写的是拍摄时的数）


def compare(claimed: float, actual: float, label: str) -> tuple[str, str]:
    """返回 (状态, 说明)。"""
    if actual == 0:
        return "⚠️", f"{label}: 声称 {claimed:g}，实际为 0"
    diff = (actual - claimed) / actual
    if abs(diff) <= TOL:
        return "✅", f"{label}: 声称 {claimed:g} ≈ 实际 {actual:,g}（偏差 {diff:+.1%}）"
    if diff > TOL:
        return "❌", f"{label}: 声称 {claimed:g}，实际 {actual:,g} —— 低报 {-diff:.0%}"
    return "❌", f"{label}: 声称 {claimed:g}，实际 {actual:,g} —— 高报 {-diff:.0%}"


def check_note(path: str) -> dict:
    text = open(path, encoding="utf-8", errors="ignore").read()
    nums = extract_numbers(text)
    repos = extract_repos(text)
    res = {"file": os.path.basename(path), "claims": nums, "repos": repos,
           "facts": [], "problems": [], "_real": {}}
    if not repos:
        res["problems"].append("笔记未标注 GitHub 仓库，无法自动核实")
        return res

    real = {}
    for rp in repos[:3]:  # 最多核3 个，控制耗时
        f = verify_repo(rp)
        real[rp] = f
        if not f["ok"]:
            res["problems"].append(f"{rp}: {f.get('error')}")
            continue
        facts = [f"{rp} 真实: ★{f['stars']:,}  fork={f['forks']:,}  "
                 f"许可={f['license_resolved'] or f['license'] or '无'}  "
                 f"创建={f['created']}  push={f['pushed']}"]
        res["facts"].append(" ".join(facts))
        if f["archived"]:
            res["problems"].append(f"{rp} 已归档归档！")
        # 数字比对
        if "stars" in nums:
            res["problems"].append(compare(nums["stars"][0], f["stars"], "star 数")[1])
        for key, field, lbl in [("entries", None, "条目数"), ("topics", None, "主题数")]:
            if key in nums:
                res["problems"].append(f"ℹ️ {lbl} 声称 {nums[key][0]:g}（GitHub 无对应字段，需读README 核对）")

    # 许可证一致性
    batch = resolve_license_batch([r for r in repos[:3] if r in real and real[r]["ok"]])
    for rp, lic in batch.items():
        if lic.get("conflict"):
            res["problems"].append(f"{rp} 许可证冲突: {lic['conflict']}")
    res["_real"] = real
    return res


# ────────────────────────────────────────────────────────── 报告

def show(res: dict, verbose=True):
    print(f"\n{'=' * 62}")
    print(f"📄 {res['file']}")
    if res["claims"]:
        print("  声称的数字:")
        for k, tup in res["claims"].items():
            v, line, desc = tup[0], tup[1], tup[2]
            print(f"    · {desc} = {v:g}")
            if line:
                print(f"      「{line}」")
    if res["repos"]:
        print(f"  仓库: {', '.join(res['repos'])}")
    for f in res["facts"]:
        print(f"  实测: {f}")
    if res["problems"]:
        print("  ⚠️ 需关注:")
        for p in res["problems"]:
            print(f"     · {p}")
    else:
        print("  ✅ 无异常")


def scan(directory: str):
    files = [os.path.join(directory, f) for f in os.listdir(directory) if f.endswith(".md")]
    print(f"扫描 {directory}：{len(files)} 个 md 文件\n")
    bad = []
    for i, f in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {os.path.basename(f)[:48]}...", flush=True)
        try:
            r = check_note(f)
        except Exception as e:
            print(f"    ⚠️ 核查异常: {e}")
            continue
        hard = [p for p in r["problems"] if p.startswith("❌") or "归档" in p or "冲突" in p]
        if hard:
            bad.append((f, r))
    print(f"\n{'=' * 62}")
    print(f"扫描完成：{len(files)} 篇，{len(bad)} 篇有硬伤")
    for f, r in bad:
        print(f"\n📄 {os.path.basename(f)}")
        for p in r["problems"]:
            print(f"   · {p}")


# ────────────────────────────────────────────────────────── selftest

FIXTURES = [
    # (笔记文本, 应抽出的字段, 说明)
    ("项目拿下 25K 的 star，非常火爆", {"stars": 25000.0}, "K 后缀要还原成 25000"),
    ("已有 36,360 个 star", {"stars": 36360.0}, "带千分位的 star"),
    ("把 601 条建议按 33 个主题整理", {"entries": 601.0, "topics": 33.0}, "条目+主题"),
    ("包含 654 条建议", {"entries": 654.0}, "条目"),
    ("0.3秒极速判定", {"latency_s": 0.3}, "延迟"),
    ("定价 $29.9 一次性买断", {"price_usd": 29.9}, "价格"),
    ("没有任何数字的一段话", {}, "无数字不误抽"),
    ("star 数不是 25k 而是 30K star", {"stars": 30000.0}, "多个取首个"),
    ("见 `om-ai-lab/VLX-Seek` 仓库", {}, "仓库正则单独处理"),
    ("1234 条不是建议而是编号", {}, "「条」后必须跟建议/条目等词"),
]

REPO_FIX = [
    ("见 `om-ai-lab/VLX-Seek` 仓库", ["om-ai-lab/VLX-Seek"], "反引号内仓库名"),
    ("访问 https://github.com/khoj-ai/khoj 获取", ["khoj-ai/khoj"], "URL 仓库名"),
    ("lyswhut/lx-music. 结束", ["lyswhut/lx-music"], "去尾点"),
    ("owner/repo 是文档占位符", [], "占位符要去尾点后仍被白名单排除"),
    ("没有仓库", [], "无仓库"),
    ("路径 /opt/data/memories 和 ./cache/scratch 都不是仓库",
     [], "本地路径不得误抽成仓库"),
    ("见 README.md 与 notes.txt 文件", [], "普通文件名不得误抽"),
    ("多个：a/b/c 是路径，d/e 才是仓库", ["d/e"], "混合文本只取仓库"),
    # ↓ 实战抓出的误抽（真实笔记里出现过）：
    ("转写 via cloud/turbo 完成", [], "转写引擎名不是仓库"),
    ("遵循 FACT/ESTIMATE 标注纪律", [], "概念标签不是仓库"),
    ("抓 https://raw.githubusercontent.com/main/README.md 失败", [], "CDN 域名路径不是仓库"),
    ("见 15-小卡工作区/开源源码 目录", [], "中文本地路径不是仓库"),
    # ↓ 二次实战抓出的噪音（补仓库名后重跑核查时出现）：
    ("重跑：python3 /opt/data/memories/factcheck.py <本文件>", [], "脚本路径不是仓库"),
    ("形如 owner/repo 的占位符", [], "文档占位符不是真仓库"),
    ("见 skills/data.json 与 config.yml", [], "配置文件路径不是仓库"),
]


def selftest():
    print("=== factcheck.py --selftest ===\n")
    npass = nfail = 0
    for text, want, desc in FIXTURES:
        got = extract_numbers(text)
        ok = set(got) == set(want)
        if ok:
            for k, v in want.items():
                if abs(got[k][0] - v) > 1e-6:
                    ok = False
                    break
        npass, nfail = npass + ok, nfail + (not ok)
        print(f"{'✅' if ok else '❌'} 数字抽取 · {desc}")
        if not ok:
            print(f"     期望 {want}  实得 { {k: round(v[0],3) for k,v in got.items()} }")

    for text, want, desc in REPO_FIX:
        got = extract_repos(text)
        ok = got == want
        npass, nfail = npass + ok, nfail + (not ok)
        print(f"{'✅' if ok else '❌'} 仓库抽取 · {desc}")
        if not ok:
            print(f"     期望 {want}  实得 {got}")

    # 比对逻辑
    print()
    for claimed, actual, want_state, desc in [
        (25000, 36360, "❌", "低报要被抓出"),
        (36360, 36360, "✅", "一致"),
        (35000, 36360, "✅", "5% 内算容差"),
        (601, 654, "❌", "条目数不符"),
    ]:
        st, msg = compare(claimed, actual, "测试")
        ok = st == want_state
        npass, nfail = npass + ok, nfail + (not ok)
        print(f"{'✅' if ok else '❌'} 比对 · {desc}  [{msg}]")
        if not ok:
            print(f"     期望 {want_state}  实得 {st}")

    print(f"\n结果: {npass}/{npass + nfail} 通过")
    if nfail == 0:
        print("✅ 自检通过 —— 抽取与比对逻辑可信")
    else:
        print("❌ 自检失败 —— 不可用于真实结论")
    return 1 if nfail else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        sys.exit(2)
    if "--selftest" in a:
        sys.exit(selftest())
    if "--scan" in a:
        scan(a[a.index("--scan") + 1])
    else:
        for f in a:
            try:
                show(check_note(f))
            except Exception as e:
                print(f"\n❌ {f} 核查异常: {e}")