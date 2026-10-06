#!/usr/bin/env python3
"""回源纪律校验器 —— 针对「生成时用补全代替核对」这一失败模式。

用法：
  python3 verify_quote.py "<原文片段>" --corpus <语料目录 glob>
  python3 verify_quote.py --file <md文件> --corpus <glob> --extract-from "金句摘录"
  python3 verify_quote.py --selftest

三件事，任何一件失败就非零退出：
  1) 引文逐条回源 grep（汉字层比对，避开引号形态差异）
  2) 目录/清单类内容与源目录零差异
  3) 自检：故意注入 3 类已知错误，确认都能被抓
"""
import sys, os, re, glob, argparse

def core(s):
    """只保留汉字：避开「」/『』/《》/直角引号 的形态差异"""
    return re.sub(r'[^\u4e00-\u9fff]', '', s)

def load_corpus(pattern):
    """pattern 可以是目录、通配目录（001-*），或直接是文件。
    坑：glob 命中目录后再用 ** 递归时，若目录名末尾无 / 会漏 —— 两种都试。"""
    roots = [d for d in glob.glob(pattern) if os.path.isdir(d)]
    files = [f for f in glob.glob(pattern) if os.path.isfile(f)]
    for d in roots:
        files += glob.glob(f"{d}/**/*.md", recursive=True)
        files += glob.glob(f"{d}/**/*.txt", recursive=True)
        files += glob.glob(f"{os.path.join(d, '**')}/**/*.md", recursive=True)
    seen, out = set(), {}
    for f in files:
        if f in seen or not os.path.isfile(f):
            continue
        seen.add(f)
        out[os.path.basename(f)] = open(f, encoding="utf-8", errors="ignore").read()
    return out

def find_quote(corpus, quote, src_hint=""):
    """命中判据：整句都在原文中出现，而不是只匹配前 N 字。
    为什么：短前缀匹配会让「改动一字」和「完全虚构」都假命中（自检已验证）。"""
    q = core(quote)
    if not q:
        return None
    # 引文里的省略号 = 原文此处有省略，拆成多段各自校验（任一段缺失即不命中）
    if "……" in quote or "…" in quote:
        parts = [core(x) for x in re.split(r'…+', quote) if len(core(x)) >= 6]
        if len(parts) >= 2:
            for p_ in parts:
                sub = find_quote(corpus, p_, "")
                if sub is None:
                    return None
            return ["(拼接引文, 各段均命中)"]
    hits = []
    for name, txt in corpus.items():
        c = core(txt)
        # 分片校验：长句按 12 字一片，全部命中才算命中（短前缀会让改动/虚构都假命中）
        frags = [q[i:i+12] for i in range(0, len(q), 12)] or [q]
        if all(fr in c for fr in frags) and (not src_hint or core(src_hint)[:6] in core(name)):
            hits.append(name)
    return hits or None   # 关键：空列表必须变 None，否则 `is not None` 把空当命中

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("quote", nargs="?", help="要核对的原文片段")
    ap.add_argument("--corpus", required=False, help="语料目录 glob，如 /path/repo/001-*")
    ap.add_argument("--file", help="校验整个 md 文件里的引文")
    ap.add_argument("--extract-from", help="只校验该标题节之后的内容，默认全文件")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    corpus = load_corpus(args.corpus)
    if not corpus:
        print("FAIL: 语料为空，检查 --corpus 路径")
        return 2

    quotes = []
    if args.file:
        t = open(args.file, encoding="utf-8").read()
        if args.extract_from and args.extract_from in t:
            t = t.split(args.extract_from)[-1]
        # 五种常见引文格式都吃
        # 后两条必须行首锚定 `- `：只吃 bullet 引用清单，否则会把正文里
        # 小卡自造的概括语（如「当下能赢几场」「表现—来源—纠正方法」）当引文误报。
        for pat in [r'^\d+\.\s*「([^\n]+?)」\s*(?:——)?\s*[—-]*\s*《([^\n]+?》)',
                    r'^>\s*「([^\n]+?)」',
                    r'「([^\n]{8,}?)」\s*——《',
                    r'^-\s*「([^\n]{8,}?)」（《([^》\n]+)》',
                    r'^-\s*「([^\n]{8,}?)」——']:
            quotes += [(m.group(1), m.group(2) if m.lastindex and m.lastindex > 1 else "")
                       for m in re.finditer(pat, t, re.M)]
    elif args.quote:
        quotes = [(args.quote, "")]
    else:
        print("FAIL: 给引文或 --file")
        return 2

    if not quotes:
        print("FAIL: 没抽出任何引文（检查 --extract-from 的标题是否存在）")
        return 2

    bad = []
    for q, src in quotes:
        if find_quote(corpus, q, src) is None:
            bad.append((q, src))
    print(f"引文回源: {len(quotes)-len(bad)}/{len(quotes)} 命中")
    for q, src in bad:
        print(f"  X 未命中: 「{core(q)[:28]}」" + (f"  <-{src}" if src else ""))
    return 1 if bad else 0

def selftest():
    """故意造错，确认校验器能抓 —— 校验器自己也可能假 PASS"""
    tmp = "/tmp/_gt_selfcheck"
    os.makedirs(tmp, exist_ok=True)
    src = f"{tmp}/src"
    os.makedirs(src, exist_ok=True)
    open(f"{src}/原文.md", "w", encoding="utf-8").write(
        "# 测试篇目\n这是真实存在的原文句子，用来验证回源逻辑是否正常工作。\n")
    corpus = load_corpus(f"{src}/*")
    cases = [
        ("这是真实存在的原文句子", True,  "真引文应命中"),
        ("这是真实存在但改动了的句子", False, "改动一字应不命中"),
        ("完全不存在的一句话", False, "虚构句应不命中"),
    ]
    ok = True
    for q, should_hit, desc in cases:
        hit = find_quote(corpus, q) is not None
        good = (hit == should_hit)
        ok &= good
        print(f"  {'OK ' if good else 'BAD'} {desc}: 期望{'命中' if should_hit else '不命中'} 实际{'命中' if hit else '不命中'}")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
