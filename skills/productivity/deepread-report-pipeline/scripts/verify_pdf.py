#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF 交付验收门禁 —— 六项硬门槛，退出码 0 = 全过。

用法:
  python3 verify_pdf.py 报告.pdf \
      --keywords "定位" "详情页" "复盘" \
      --probes "资产唯一特征串1" "资产唯一特征串2" \
      --out /opt/data/cache/scratch/pdf_text.txt

依赖: pymupdf（版式）+ pypdf（文本可搜索性）
  uv pip install --quiet --python /opt/data/.venv-browser/bin/python pypdf pymupdf
"""
import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--keywords", nargs="*", default=[],
                    help="报告必须出现的关键词，逐个检查命中")
    ap.add_argument("--probes", nargs="*", default=[],
                    help="长文报告里每个 Prompt/模板的唯一特征串")
    ap.add_argument("--secrets", nargs="*",
                    default=["cookie", "Cookie", "token", "password", "密码"],
                    help="不应出现的敏感串，命中即 FAIL")
    ap.add_argument("--out", default="", help="把抽取的全文写到该路径")
    args = ap.parse_args()

    import pymupdf

    try:
        import pypdf
    except ImportError:
        print("FAIL: 缺 pypdf —— uv pip install --python <venv>/bin/python pypdf pymupdf")
        return 2

    doc = pymupdf.open(args.pdf)
    H = doc[0].rect.height
    W = doc[0].rect.width
    footer_y = H - 40          # 页脚带：页码在这里，别当溢出
    margin_min = 25
    fails = []

    # --- 1) 内嵌字体 ---
    fonts = {f[3]: f[1] for p in doc for f in p.get_fonts(full=True) if len(f) > 1 and f[1]}
    print(f"[1] 内嵌字体: {len(fonts)}")
    for name, ext in sorted(fonts.items()):
        print(f"      {name} -> {ext}")
    if not fonts:
        fails.append("无内嵌字体")

    # --- 2) 乱码 U+FFFD ---
    tofu_pages = [i + 1 for i, p in enumerate(doc) if "�" in p.get_text()]
    print(f"[2] 乱码页: {tofu_pages or '无'}")
    if tofu_pages:
        fails.append(f"乱码页 {tofu_pages}")

    # --- 3) 正文溢出（先剔页脚）---
    over = []
    for i, p in enumerate(doc):
        for b in p.get_text("blocks"):
            x0, y0, x1, t = b[0], b[1], b[2], b[4].strip()
            if not t or y0 > footer_y:
                continue          # 页脚不算
            if x1 > W - margin_min or x0 < 8:
                over.append((i + 1, round(x0), t[:30]))
    print(f"[3] 正文越界: {len(over)}")
    for o in over[:5]:
        print("      p%-3d x=%s  %s" % o)
    if over:
        fails.append(f"正文越界 {len(over)} 块")

    # --- 4) 右边距 ---
    bodies = [b for p in doc for b in p.get_text("blocks")
              if b[4].strip() and b[1] <= footer_y]
    if bodies:
        right = W - max(b[2] for b in bodies)
        print(f"[4] 右边距: {right:.0f}pt")
        if right < margin_min:
            fails.append(f"右边距不足 {right:.0f}pt")
    else:
        print("[4] 右边距: 无正文块")
        fails.append("无正文块")

    # --- 5) 内容完整性 ---
    text = "\n".join((p.extract_text() or "")
                     for p in pypdf.PdfReader(args.pdf).pages)
    print(f"[5] 抽取字符: {len(text)}")
    if args.keywords:
        miss = [k for k in args.keywords if k not in text]
        print(f"      关键词 {len(args.keywords)-len(miss)}/{len(args.keywords)}  缺: {miss or '无'}")
        if miss:
            fails.append(f"缺关键词 {miss}")
    if args.probes:
        gone = [x for x in args.probes if x not in text]
        print(f"      资产探针 {len(args.probes)-len(gone)}/{len(args.probes)}  缺: {gone or '无'}")
        if gone:
            fails.append(f"缺资产 {gone}")
    hits = [s for s in args.secrets if s in text]
    print(f"      敏感串: {hits or '无'}")
    if hits:
        fails.append(f"敏感串 {hits}")

    # --- 6) 书签 ---
    toc = doc.get_toc()
    print(f"[6] 书签: {len(toc)} 条")
    if not toc:
        fails.append("无书签")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"      全文已导出: {args.out}")

    print(f"\n页数: {doc.page_count}")
    if fails:
        print("\nFAIL:")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\nPASS: 六项门禁全过")
    return 0


if __name__ == "__main__":
    sys.exit(main())