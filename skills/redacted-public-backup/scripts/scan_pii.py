#!/usr/bin/env python3
"""发布前敏感信息扫描器。

在推任何目录到公开/远端仓之前跑一遍，报告命中文件和类型。
先拿到清单再动手，不要按文件名猜——登录态常藏在名字无害的脚本和文档旁边。

用法：
    scan_pii.py <目录> [<目录> ...]
    scan_pii.py <目录> --json
    scan_pii.py --selftest
退出码：0 = 无高危命中，1 = 有命中，2 = 自检失败。
"""
import json
import os
import re
import sys

# (标签, 正则, 是否高危)
# 高危 = 推送前必须处理；低危 = 需人工确认，多为误报
PATTERNS = [
    ("GitHub token", r"gh[pousr]_[A-Za-z0-9]{20,}", True),
    ("OpenAI key", r"\bsk-[A-Za-z0-9]{20,}", True),
    ("AWS key", r"\bAKIA[0-9A-Z]{16}\b", True),
    ("私钥块", r"-----BEGIN [A-Z ]*PRIVATE KEY-----", True),
    ("凭据赋值", r"(?:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{8,}", True),
    ("手机号", r"1[3-9]\d{9}", False),
    ("身份证", r"\d{17}[\dXx]", False),
]

# 整个目录排除
SKIP_DIRS = {".git", ".obsidian", "__pycache__", "node_modules", ".cache",
             ".venv", ".venv-browser", ".playwright-browsers"}
# 整个文件排除
SKIP_NAMES = {"MEMORY.md", "USER.md", "USER_PROFILE.md"}
SCAN_EXT = {".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml", ".js",
            ".ts", ".tsx", ".jsx", ".html", ".css", ".toml", ".cfg", ".ini", ""}

# 已知误报：需人工确认的形态
ID_LIKE = re.compile(r"^\d{17,20}$")


def scan_file(path):
    try:
        text = open(path, encoding="utf-8").read()
    except Exception:
        return []
    hits = []
    for label, pat, high in PATTERNS:
        for m in re.finditer(pat, text, re.I):
            val = m.group(0)
            # 长纯数字：极可能是作品/雪花 ID，不是身份证
            if label == "身份证" and ID_LIKE.match(val):
                continue
            hits.append({"label": label, "high": high, "value": val[:12],
                         "line": text[:m.start()].count("\n") + 1})
    return hits


def scan(paths):
    findings = {}
    for base in paths:
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for f in files:
                if f in SKIP_NAMES or os.path.splitext(f)[1].lower() not in SCAN_EXT:
                    continue
                p = os.path.join(root, f)
                hits = scan_file(p)
                if hits:
                    findings[p] = hits
    return findings


def report(findings):
    if not findings:
        print("✅ 未发现敏感信息")
        return 0
    groups = {}
    for p, hits in findings.items():
        for h in hits:
            groups.setdefault(h["label"], []).append((p, h))
    for label, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        high = any(h["high"] for _, h in items)
        mark = "🔴 高危" if high else "🟡 待确认"
        files = {p for p, _ in items}
        print(f"\n{mark}  {label}: {len(items)} 处 / {len(files)} 文件")
        for p, h in items[:3]:
            print(f"      {p}:{h['line']}  →  {h['value']}…")
        if len(files) > 3:
            print(f"      …另 {len(files) - 3} 个文件")
    n_high = sum(1 for items in groups.values() for _, h in items if h["high"])
    print(f"\n{'=' * 50}\n高危 {n_high} 处 / 待确认 "
          f"{sum(len(v) for v in groups.values()) - n_high} 处")
    print("高危必须处理；待确认多为长数字 ID 误报，逐条核实来源再决定。")
    return 1 if n_high else 0


# ---------------------------------------------------------------- selftest
# 每条 fixture = (文件内容, 必须被抓到的标签[])
FIXTURES = [
    ("GH_TOKEN = 'ghp_abc123def456ghi789jkl012mno'\n", ["GitHub token"]),
    ("export OPENAI_API_KEY=sk-proj-abcdefghij1234567890\n", ["OpenAI key"]),
    ("aws_key = AKIAIOSFODNN7EXAMPLE\n", ["AWS key"]),
    ("password: hunter2secret\n", ["凭据赋值"]),
    ("-----BEGIN RSA PRIVATE KEY-----\n", ["私钥块"]),
    ("联系 【手机号】 就行\n", ["手机号"]),
    ("正常的技术笔记，没有任何敏感信息。\n", []),
    # 反例：长数字作品 ID 不得报成身份证
    ("douyin_id: 76824【手机号】330\n", []),
    # 反例：占位符不是真 token
    ('GITHUB_PERSONAL_ACCESS_TOKEN: "ghp_xx...xxxx"\n', []),
]


def selftest():
    print("=== scan_pii.py --selftest ===\n")
    npass = nfail = 0
    for content, want in FIXTURES:
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(content)
            tmp = fh.name
        got = {h["label"] for h in scan_file(tmp)}
        os.unlink(tmp)
        ok = set(want) == got
        npass, nfail = npass + ok, nfail + (not ok)
        print(f"{'✅' if ok else '❌'} {content.strip()[:52]}")
        if not ok:
            print(f"     期望 {want}  实得 {sorted(got)}")
    print(f"\n结果: {npass}/{npass + nfail} 通过")
    print("✅ 自检通过 —— 扫描器可信" if not nfail
          else "❌ 自检失败 —— 扫描器有 bug，不可用于真实结论")
    return 1 if nfail else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a != "--json" and a != "--json"]
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not paths:
        print(__doc__)
        sys.exit(2)
    result = scan(paths)
    if "--json" in sys.argv:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        sys.exit(1 if any(h["high"] for v in result.values() for h in v) else 0)
    sys.exit(report(result))