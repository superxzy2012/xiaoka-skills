#!/usr/bin/env python3
"""许可证回源解析器 —— 解决 GitHub API 返回 NOASSERTION 的坑。

问题：GitHub 用 licensee 识别 SPDX。仓库 LICENSE 文件若在正文前加了自定义措辞
（如 "This program is licensed under the GNU Affero General Public License v3.0 only."），
识别失败 → API 返回 NOASSERTION，容易被误读成「无许可证」。

做法：API 结果只作参考，一律回源拉原始 LICENSE 文本，按特征串自行判定，
并输出商业使用友好度分级。自带 --selftest（反例必须能被抓出）。

用法：
    resolve_license.py owner/repo [owner/repo ...]
    resolve_license.py --selftest
"""
import base64
import json
import os
import re
import subprocess
import sys

GH = os.environ.get("GH_BIN", "/opt/data/bin/gh")
ENV = {**os.environ,
       "HOME": os.environ.get("HERMES_HOME", "/opt/data/home"),
       "GH_CONFIG_DIR": os.environ.get("HERMES_HOME", "/opt/data/home") + "/.config/gh"}

# (正则, SPDX, 友好度) —— 顺序即优先级，必须严格按此顺序。
# 关键 1：禁商用/专有必须排在 MIT 和 AGPL 之前，否则「非商用+MIT特征」会被误判成 MIT。
# 关键 2：禁商用只认「授权/限制性声明」句式，绝不认条款细则里的用法描述。
#   反例：AGPL-3.0 正式文本第 6(b) 节含
#   "This alternative is allowed only occasionally and noncommercially" ——
#   那是「偶尔且非商业性地附源码」的条件，不是禁止商用。
#   若用裸 noncommercial 匹配，标准 AGPL 全文会被误判成「禁止商用」。
#   故要求声明句式：licensed ... for non-commercial / not licensed for commercial use。
NOCOMMERCIAL = (r"(?:licen[cs]ed|licen[cs]e|use|usage|distribution|redistribution|permission)"
                r"[\s\S]{0,80}?(?:non-?commercial|not\s+for\s+commercial)"
                r"|(?:non-?commercial)[\s\S]{0,40}?(?:use|licen[cs]e|distribution)"
                r"|禁止商用|不得用于商业")
RULES = [
    (NOCOMMERCIAL, "非商用", "no-commercial"),
    (r"all rights reserved|proprietary and confidential|is proprietary", "专有", "proprietary"),
    (r"AFFERO GENERAL PUBLIC LICENSE|GNU AFFERO", "AGPL-3.0", "copyleft-strong"),
    (r"SERVER PUBLIC LICENSE", "SSPL-1.0", "copyleft-strong"),
    (r"BUSINESS SOURCE LICENSE|BUSL", "BUSL-1.1", "copyleft-source"),
    (r"MOZILLA PUBLIC LICENSE", "MPL-2.0", "copyleft-weak"),
    (r"GNU LESSER GENERAL PUBLIC LICENSE|LESSER GENERAL PUBLIC", "LGPL", "copyleft-weak"),
    (r"GNU GENERAL PUBLIC LICENSE", "GPL", "copyleft-strong"),
    (r"APACHE LICENSE|Apache License", "Apache-2.0", "permissive"),
    (r"MIT License|Permission is hereby granted, free of charge", "MIT", "permissive"),
    (r"BSD \d-Clause|Redistribution and use in source and binary forms", "BSD", "permissive"),
    (r"Creative Commons Zero|CC0", "CC0-1.0", "public-domain"),
    (r"THE UNLICENSE|This is free and unencumbered software", "Unlicense", "public-domain"),
    (r"Creative Commons Attribution", "CC-BY", "permissive-attribution"),
]

FRIENDLY = {
    "permissive": "宽松 —— 可闭源商用，保留版权声明",
    "permissive-attribution": "较宽松 —— 需署名",
    "public-domain": "无限制",
    "copyleft-weak": "弱 copyleft —— 动态链接可闭源",
    "copyleft-strong": "强 copyleft —— 闭源商用前必须审",
    "copyleft-source": "source-available —— 非 OSI 认证",
    "no-commercial": "禁止商用",
    "proprietary": "专有 —— 默认无授权",
    "unknown": "无法判定 —— 需人工阅读",
}


def gh(args, timeout=40):
    r = subprocess.run([GH, "api"] + args, capture_output=True, text=True, env=ENV, timeout=timeout)
    return r.stdout


def classify(text):
    """回源判定。text 为 LICENSE 原文。返回 (spdx, friendliness) 或 (None, None)。"""
    if not text or not text.strip():
        return None, None
    for pat, spdx, friend in RULES:
        if re.search(pat, text, re.I):
            return spdx, friend
    return None, None


def resolve(repo):
    """解析一个 owner/repo。返回核实结果 dict。"""
    out = {"repo": repo}
    try:
        meta = json.loads(gh([f"repos/{repo}"]))
        out["stars"] = meta.get("stargazers_count")
        out["api_license"] = (meta.get("license") or {}).get("spdx_id") or None
    except Exception:
        out["api_license"] = None
        out["stars"] = None
    text, src = None, None
    raw = gh([f"repos/{repo}/license", "--jq", ".content"])
    if raw.strip():
        try:
            text = base64.b64decode(raw.strip()).decode("utf-8", "ignore")
            src = "license-endpoint"
        except Exception:
            pass
    if not text:
        for br in ("main", "master", "develop"):
            r = subprocess.run(
                ["curl", "-sfL", "-m", "20",
                 f"https://raw.githubusercontent.com/{repo}/{br}/LICENSE"],
                capture_output=True, text=True)
            if r.returncode == 0 and r.stdout.strip():
                text, src = r.stdout, f"raw/{br}/LICENSE"
                break
    out["source"] = src
    out["has_license_file"] = bool(text and text.strip())
    spdx, friend = classify(text)
    out["resolved"] = spdx
    out["friendliness"] = friend
    out["needs_review"] = spdx in (None, "非商用", "专有") or (friend == "copyleft-strong")
    api = out["api_license"]
    if api and spdx and api != spdx:
        out["conflict"] = f"API={api} vs 回源={spdx}"
    elif api == "NOASSERTION" and spdx:
        out["note"] = "API 无法识别（NOASSERTION），回源已判定"
    return out


def show(r):
    api = r["api_license"] or "无"
    res = r["resolved"] or "❌ 无法判定"
    star = f"{r['stars']:,}" if isinstance(r.get("stars"), int) else "?"
    print(f"\n{r['repo']}  ★{star}")
    print(f"  API 声明 : {api}")
    print(f"  回源判定 : {res}   (来源: {r['source'] or '无 LICENSE 文件'})")
    if r.get("conflict"):
        print(f"  ⚠️ 冲突  : {r['conflict']}")
    if r.get("note"):
        print(f"  ℹ️ {r['note']}")
    if r["friendliness"]:
        print(f"  商用友好 : {FRIENDLY.get(r['friendliness'], r['friendliness'])}")
    print(f"  需人工审 : {'是' if r['needs_review'] else '否'}")


FIXTURES = [
    ("自定义措辞+AGPL（顶部声明覆盖全文的情形）",
     "Prompt Optimizer\nCopyright (C) 2025 someone\n\n"
     "This program is licensed under the GNU Affero General Public License v3.0 only.\n"
     "See the full license text below.\n\n"
     "                    GNU AFFERO GENERAL PUBLIC LICENSE\n"
     "                       Version 3, 19 November 2007\n",
     ("AGPL-3.0", "copyleft-strong")),
    ("纯 MIT",
     "MIT License\n\nCopyright (c) 2026 Someone\n\n"
     "Permission is hereby granted, free of charge, to any person obtaining a copy\n",
     ("MIT", "permissive")),
    ("纯 GPL-3.0（不得误判成 AGPL）",
     "                    GNU GENERAL PUBLIC LICENSE\n"
     "                       Version 3, 29 June 2007\n",
     ("GPL", "copyleft-strong")),
    ("禁商用条款（不得被 MIT 特征覆盖）",
     "This software is licensed for non-commercial use only. "
     "Commercial use requires a separate agreement.\n"
     "Permission is hereby granted, free of charge, to any person obtaining a copy\n",
     ("非商用", "no-commercial")),
    ("专有声明",
     "All rights reserved. This code is proprietary and confidential.\n",
     ("专有", "proprietary")),
    ("Apache-2.0",
     "                                 Apache License\n"
     "                           Version 2.0, January 2004\n",
     ("Apache-2.0", "permissive")),
    ("空文件", "", (None, None)),
    ("无法识别的怪文本", "blah blah nothing license-like here\n", (None, None)),
    # ↓ 真实事故：标准 AGPL-3.0 全文曾被裸 noncommercial 规则误判为「禁止商用」。
    ("AGPL 全文 6(b) 节含 noncommercially（不得误判禁商用）",
     "                    GNU AFFERO GENERAL PUBLIC LICENSE\n"
     "                       Version 3, 19 November 2007\n\n"
     "  c) Convey individual copies of the object code with a copy of the\n"
     "     written offer to provide the Corresponding Source.  This\n"
     "     alternative is allowed only occasionally and noncommercially, and\n"
     "     only if you received the object code with such an offer, in accord\n"
     "     with subsection 6b.\n",
     ("AGPL-3.0", "copyleft-strong")),
    # ↓ 真实事故：MIT 正文 + 尾部非商用声明
    ("MIT 正文后附「non-commercial use only」声明",
     "MIT License\n\nCopyright (c) 2026 Someone\n\n"
     "Permission is hereby granted, free of charge, to any person obtaining a copy\n\n"
     "This software is licensed for non-commercial use only.\n",
     ("非商用", "no-commercial")),
]


def selftest():
    print("=== resolve_license.py --selftest ===\n")
    npass = nfail = 0
    for name, text, want in FIXTURES:
        got = classify(text)
        ok = got == want
        npass, nfail = npass + ok, nfail + (not ok)
        print(f"{'✅' if ok else '❌'} {name}")
        if not ok:
            print(f"     期望 {want}  实得 {got}")
    print(f"\n结果: {npass}/{npass + nfail} 通过")
    if nfail == 0:
        print("✅ 自检通过 —— 判定逻辑可信")
    else:
        print("❌ 自检失败 —— 判定逻辑有 bug，不可用于真实结论")
    return 1 if nfail else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if not args:
        print(__doc__)
        sys.exit(2)
    results = [resolve(r) for r in args]
    for r in results:
        show(r)
    flagged = [r["repo"] for r in results if r["needs_review"]]
    print(f"\n{'=' * 50}")
    print(f"检查 {len(results)} 个仓库，需人工审: {len(flagged)}")
    for f in flagged:
        print(f"  → {f}")
    sys.exit(0)