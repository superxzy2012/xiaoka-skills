#!/usr/bin/env python3
"""知识库体检 —— 不依赖外部语料的质量检查。

扫 Obsidian vault 全部 md，找机器可判定的问题：
  1. 乱码字符（U+FFFD 替换符，通常来自抓取/转码失败）
  2. 引号/书名号不配对（排除代码块与表格行，避免示例文本误报）
  3. 占位符残留（TODO / FIXME / {{ }} 等）
  4. 近空文件
  5. 可选：引文回源（给了 --corpus 时启用）

用法：
  python3 kb_audit.py                                  # 扫默认 vault
  python3 kb_audit.py --vault /path/to/vault
  python3 kb_audit.py --corpus '/path/to/src/*'       # 额外做引文回源
  python3 kb_audit.py --json                          # 机器可读输出
  python3 kb_audit.py --max-detail 20

退出码：0 = 无问题或仅 WARN；1 = 有 ERROR 级问题。
"""
import os, re, sys, json, argparse, collections

DEFAULT_VAULT = "/opt/nas/volume2/2-AI/obsidian_vault"
SKIP_DIRS = {".git", ".obsidian", ".obsidian-mcp", "attachments", "node_modules"}
PLACEHOLDERS = ["TODO", "FIXME", "XXX", "待补", "待填", "占位", "{{", "}}", "<<", ">>"]


def strip_code(t):
    """去掉代码块、行内代码、表格行——里面的引号是示例文本，不能算不配对"""
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"`[^`\n]*`", "", t)
    t = re.sub(r"^\s*\|.*\|\s*$", "", t, flags=re.M)
    return t


def list_md(vault):
    out = []
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith(".md"):
                out.append(os.path.join(root, f))
    return out


def audit(vault, corpus_glob=None, max_detail=20):
    files = list_md(vault)
    issues = collections.defaultdict(list)
    stats = {"files": len(files), "bytes": 0}

    for path in files:
        try:
            raw = open(path, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            issues["读取失败"].append((os.path.basename(path), str(e)[:60]))
            continue
        stats["bytes"] += len(raw)
        name = os.path.basename(path)
        body = strip_code(raw)

        n_bad = body.count("�")
        if n_bad:
            issues["乱码字符"].append((name, f"{n_bad} 处"))

        for op, cl, label in [("「", "」", "「」"), ("『", "』", "『』"), ("《", "》", "《》")]:
            a, b = body.count(op), body.count(cl)
            if a != b:
                issues[f"{label}不配对"].append((name, f"{op}×{a} {cl}×{b}"))

        for ph in PLACEHOLDERS:
            k = body.count(ph)
            if k:
                issues[f"占位符 {ph}"].append((name, f"{k} 处"))

        if len(raw.strip()) < 50:
            issues["近空文件"].append((name, f"{len(raw.strip())} 字符"))

    # 可选：引文回源
    if corpus_glob:
        sys.path.insert(0, "/opt/data/skills/ground-truth-discipline/scripts")
        try:
            import verify_quote as V
        except ImportError:
            issues["回源不可用"].append(("", "找不到 verify_quote.py"))
        else:
            corpus = V.load_corpus(corpus_glob)
            pat = re.compile(r"「([^」]{10,300})」[^》\n]{0,8}《([^》\n]{2,40})》")
            ok = bad = 0
            for path in files:
                try:
                    t = open(path, encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for m in pat.finditer(t):
                    q, src = m.group(1), m.group(2)
                    if V.find_quote(corpus, q, src) is None:
                        bad += 1
                        issues["引文回源失败"].append((os.path.basename(path), f"《{src}》「{V.core(q)[:24]}」"))
                    else:
                        ok += 1
            stats["引文"] = f"{ok} 命中 / {bad} 失败"

    stats["问题类别"] = len(issues)
    stats["问题总数"] = sum(len(v) for v in issues.values())
    return stats, issues, max_detail


SEVERITY = {
    "乱码字符": "ERROR",
    "引文回源失败": "ERROR",
    "读取失败": "ERROR",
    "「」不配对": "WARN",
    "『』不配对": "WARN",
    "《》不配对": "WARN",
    "近空文件": "WARN",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=DEFAULT_VAULT)
    ap.add_argument("--corpus", help="语料 glob，启用引文回源")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-detail", type=int, default=20)
    args = ap.parse_args()

    stats, issues, md = audit(args.vault, args.corpus, args.max_detail)

    if args.json:
        print(json.dumps(
            {"stats": stats,
             "issues": {k: v[:md] for k, v in issues.items()}},
            ensure_ascii=False, indent=2))
    else:
        print(f"扫描 {stats['files']} 个 md / {stats['bytes']/1024:.0f} KB"
              + (f" / 引文 {stats['引文']}" if "引文" in stats else ""))
        print("=" * 56)
        if not issues:
            print("干净：未发现问题。")
            return 0
        for k, v in sorted(issues.items(), key=lambda x: -len(x[1])):
            sev = SEVERITY.get(k.split("（")[0], "WARN")
            print(f"\n[{sev}] {k} —— {len(v)} 处")
            for name, detail in v[:md]:
                print(f"    {name[:52]:<54} {detail}")
            if len(v) > md:
                print(f"    ... 另有 {len(v)-md} 处")
        print("\n" + "=" * 56)
        errs = sum(len(v) for k, v in issues.items() if SEVERITY.get(k.split("（")[0]) == "ERROR")
        print(f"合计 {stats['问题总数']} 处，其中 ERROR {errs} 处。")

    return 1 if any(SEVERITY.get(k.split("（")[0]) == "ERROR" for k in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
