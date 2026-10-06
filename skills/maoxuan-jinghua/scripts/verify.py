#!/usr/bin/env python3
"""毛选蒸馏产物自动校验器 —— 独立于写作过程。
用法: python3 verify.py [产物根目录]
校验三项: 1) 金句回源 grep  2) 篇目概览与源目录零差异  3) 编号连续/无占位符
"""
import sys, os, re, glob

# 语料放持久目录：scratch 空闲 24h 会被剪，剪掉后校验器会以 IndexError 崩掉而不是明确报错
REPO = "/opt/data/cache/mzd/repo"
VOLS = {"vol1": "001-第一卷*", "vol2": "002-第二卷*", "vol3": "003-第三卷*", "vol4": "004-第四卷*", "vol5": "005-第五卷*"}

def core(s):
    """只保留汉字，避开原文引号形态差异（直角引号 vs 书名号）"""
    return re.sub(r'[^\u4e00-\u9fff]', '', s)

def load_corpus(vol):
    hits = glob.glob(f"{REPO}/{VOLS[vol]}")
    if not hits:
        sys.exit(f"FAIL: 语料缺失 {REPO}/{VOLS[vol]} —— 回源校验不能静默跳过，"
                 f"先重新拉取（见技能 ground-truth-discipline「语料必须放在 scratch 之外」）")
    d = hits[0]
    out = {}
    for f in glob.glob(f"{d}/**/*.md", recursive=True):
        key = re.sub(r'^\d+-', '', os.path.basename(f)[:-3])
        out[key] = open(f, encoding="utf-8").read()
    if not out:
        sys.exit(f"FAIL: 语料目录 {d} 下没有 .md 文件")
    return out

def check_vol(vol, corpus):
    errs, warns = [], []
    for path in sorted(glob.glob(f"references/{vol}/ch*.md")):
        t = open(path, encoding="utf-8").read()
        name = os.path.basename(path)
        # 1) 金句回源
        sec = t.split('## 金句摘录')[-1].split('## 名篇深读')[0] if '## 金句摘录' in t else t
        quotes = re.findall(r'^(\d+)\. 「([^\n]+)」——《([^\n]+?》)(?:（[^\n]*）)?\s*$', sec, re.M)
        nums = [int(n) for n, _, _ in quotes]
        if nums and nums != list(range(1, len(nums) + 1)):
            warns.append(f"{name}: 金句编号不连续 {nums}")
        bad = []
        for _, q, src in quotes:
            if not any(core(q)[:12] in core(c) and core(src)[:6] in core(fn)
                       for fn, c in corpus.items()):
                bad.append(f"[{src}] {core(q)[:24]}")
        if bad:
            errs.append(f"{name}: {len(bad)}/{len(quotes)} 金句未命中 -> " + "; ".join(bad))
        else:
            print(f"  OK {vol}/{name}: 金句 {len(quotes)}/{len(quotes)} 命中")
        # 3) 占位符/截断痕迹
        for pat, desc in [(r'\.\.\.\(\+\d+ chars', '截断痕迹'),
                          (r'[A-Za-z]{3,}[\u4e00-\u9fff]', '外文混排'),
                          (r'^(4|9)\. What$', '重复占位')]:
            if re.search(pat, t, re.M):
                warns.append(f"{name}: 发现{desc}")
    # 2) 篇目概览零差异
    for path in sorted(glob.glob(f"references/{vol}/*.md")):
        t = open(path, encoding="utf-8").read()
        m = re.search(r'## 篇目概览(.*?)(?=\n## )', t, re.S)
        if not m:
            continue
        listed_raw = [x.strip() for x in re.findall(r'^\| \d+ \| ([^|]+?) \|', m.group(1), re.M)]
        listed = {core(x) for x in listed_raw}
        src = {core(k) for k in corpus}
        # 允许源文件名含《》/?/——等，而表内是清洗后的短名：做前缀包含匹配
        def covered(a, bset):
            return any(a in b or b in a for b in bset)
        only_tbl = {x for x in listed if not covered(x, src)}
        only_src = {x for x in src if not covered(x, listed)}
        if only_tbl or only_src:
            errs.append(f"{os.path.basename(path)}: 篇目不符 表多={sorted(only_tbl)[:3]} 漏={sorted(only_src)[:3]}")
        else:
            print(f"  OK {vol}/{os.path.basename(path)}: 篇目 {len(src)}/{len(src)} 对齐")
    return errs, warns

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    os.chdir(root)
    allerr, allwarn = [], []
    for vol in VOLS:
        if not os.path.isdir(f"references/{vol}"):
            continue
        print(f"\n--- {vol} ---")
        e, w = check_vol(vol, load_corpus(vol))
        allerr += e; allwarn += w
    print("\n" + "=" * 60)
    if allerr:
        print("FAIL:")
        for x in allerr: print("  ✗ " + x)
    else:
        print("PASS: 全部校验通过")
    if allwarn:
        print("WARN:")
        for x in allwarn: print("  ! " + x)
    sys.exit(1 if allerr else 0)
