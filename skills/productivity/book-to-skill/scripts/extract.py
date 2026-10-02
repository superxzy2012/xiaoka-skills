#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
book-to-skill · extract.py
=========================
把书籍 / 文档抽取成 `full_text.txt` + `metadata.json`，供下游生成 agent skill。

CLI 契约（与 book-to-skill SKILL.md Step 2 对齐，不可改）：
    python3 extract.py <路径|glob>... --mode <text|technical> --install-missing <ask|yes|no>
    python3 extract.py --check          # 环境预检，逐格式报告可用抽取器

产物（工作目录名每次随机，避免并发覆盖）：
    <workdir>/full_text.txt
    <workdir>/metadata.json

Hermes 适配：本脚本原为上游缺失文件，由小卡补写（2026-10-02）。
"""

from __future__ import annotations

import argparse
import glob as globmod
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------- 常量

SUPPORTED = {
    ".pdf", ".epub", ".docx", ".txt", ".md", ".markdown", ".rst",
    ".adoc", ".html", ".htm", ".rtf", ".mobi", ".azw", ".azw3",
}

CLI_TEMPLATE = {
    "pdftotext":     ["pdftotext", "-layout", "{src}", "-"],
    "pandoc":        ["pandoc", "-t", "plain", "{src}"],
    "ebook-convert": ["ebook-convert", "{src}", "-"],
}

# py 库名 → markitdown extras 需求
INSTALL_HINT = {
    "pdf": "pymupdf",
    "epub": "markitdown[all]",
    "mobi": "markitdown[all]",
    "azw": "markitdown[all]",
    "azw3": "markitdown[all]",
    "docx": "docx2txt",
    "html": None,
    "rtf": None,
    "txt": None,
    "md": None,
    "markdown": None,
    "rst": None,
    "adoc": None,
}

FALLBACK_PKGS = ["pymupdf", "markitdown[all]", "docx2txt"]


# ---------------------------------------------------------------- 工具

def log(msg: str = "") -> None:
    print(msg, flush=True)


def have(mod: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(mod) is not None
    except Exception:
        return False


def human(n: float) -> str:
    for unit, div in (("K", 1_000), ("M", 1_000_000)):
        if n >= div:
            return f"{n / div:.1f}{unit}"
    return f"{int(n)}"


def estimate_tokens(text: str) -> int:
    """粗估 token：CJK 约 1 字 1 token，其余约 1 词 1.35 token。"""
    cjk = len(re.findall(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", text))
    rest = len(text) - cjk
    return int(cjk + rest / 1.35)


def decode_bytes(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gb18030", "big5", "latin-1"):
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    if have("charset_normalizer"):
        try:
            from charset_normalizer import from_bytes
            best = from_bytes(raw).best()
            if best is not None:
                return str(best)
        except Exception:
            pass
    return raw.decode("utf-8", errors="replace")


def strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|h[1-6]|tr)>", "\n", html)
    html = re.sub(r"<[^>]+>", " ", html)
    html = (html.replace("&nbsp;", " ").replace("&amp;", "&")
                .replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'"))
    html = re.sub(r"[ \t ]+", " ", html)
    return re.sub(r"\n{3,}", "\n\n", html).strip()


# ---------------------------------------------------------------- 抽取器

def _run_cli(tool: str, src: Path) -> str | None:
    exe = shutil.which(tool)
    if not exe:
        return None
    cmd = [exe] + [a.replace("{src}", str(src)) for a in CLI_TEMPLATE[tool]]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=300)
    except Exception:
        return None
    if r.returncode != 0 or not r.stdout:
        return None
    return decode_bytes(r.stdout)


def _pdf_pymupdf(src: Path) -> str | None:
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            return None
    try:
        doc = pymupdf.open(src)
    except Exception:
        return None
    parts = []
    for page in doc:
        parts.append(page.get_text("text") or "")
    doc.close()
    return "\n\n".join(p.strip() for p in parts if p.strip()) or None


def _pdf_pypdf(src: Path) -> str | None:
    try:
        from pypdf import PdfReader
    except ImportError:
        return None
    try:
        reader = PdfReader(str(src))
        out = "\n\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return None
    return out.strip() or None


def _markitdown(src: Path) -> str | None:
    try:
        from markitdown import MarkItDown
    except ImportError:
        return None
    try:
        res = MarkItDown(enable_plugins=False).convert(str(src))
        return (res.text_content or "").strip() or None
    except Exception:
        return None


def _docx2txt(src: Path) -> str | None:
    try:
        import docx2txt as m
    except ImportError:
        return None
    try:
        return (m.process(str(src)) or "").strip() or None
    except Exception:
        return None


def _plain(src: Path) -> str | None:
    try:
        return decode_bytes(src.read_bytes()).strip() or None
    except Exception:
        return None


def _html(src: Path) -> str | None:
    try:
        return strip_html(decode_bytes(src.read_bytes())) or None
    except Exception:
        return None


def _rtf(src: Path) -> str | None:
    try:
        raw = decode_bytes(src.read_bytes())
    except Exception:
        return None
    raw = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), raw)
    raw = re.sub(r"\\par[d]?\b", "\n", raw)
    raw = re.sub(r"\\[a-zA-Z]+-?\d*\s?", " ", raw)
    raw = raw.replace("{", "").replace("}", "")
    return re.sub(r"\n{3,}", "\n\n", raw).strip() or None


EXTRACTORS: dict[str, list[tuple[str, object]]] = {
    "pdf":      [("pymupdf", _pdf_pymupdf), ("pypdf", _pdf_pypdf),
                 ("pdftotext", None), ("markitdown", _markitdown)],
    "epub":     [("markitdown", _markitdown)],
    "docx":     [("docx2txt", _docx2txt), ("markitdown", _markitdown)],
    "html":     [("builtin", _html), ("markitdown", _markitdown)],
    "rtf":      [("builtin", _rtf), ("markitdown", _markitdown)],
    "mobi":     [("ebook-convert", None), ("markitdown", _markitdown)],
    "azw":      [("ebook-convert", None), ("markitdown", _markitdown)],
    "azw3":     [("ebook-convert", None), ("markitdown", _markitdown)],
    "txt":      [("builtin", _plain), ("markitdown", _markitdown)],
    "md":       [("builtin", _plain), ("markitdown", _markitdown)],
    "markdown": [("builtin", _plain), ("markitdown", _markitdown)],
    "rst":      [("builtin", _plain), ("markitdown", _markitdown)],
    "adoc":     [("builtin", _plain), ("markitdown", _markitdown)],
}

CLI_TOOLS = {"pdftotext", "pandoc", "ebook-convert"}


def extractor_status(fmt: str) -> tuple[bool, str]:
    for name, fn in EXTRACTORS.get(fmt, []):
        if name == "builtin":
            return True, "builtin"
        if name in CLI_TOOLS:
            if shutil.which(name):
                return True, name
        elif have(name):
            return True, name
    return False, "-"


# 最小有效文本阈值（字符）。html/rtf 去标签/去控制字后天然大幅缩水，
# 用与 pdf 相同的阈值会把「短但抽取成功」的文件误判为失败。
MIN_CHARS = {"html": 8, "rtf": 8, "txt": 8, "md": 8, "markdown": 8,
             "rst": 8, "adoc": 8}


def extract_one(src: Path, mode: str) -> tuple[str | None, str]:
    fmt = src.suffix.lower().lstrip(".")
    floor = MIN_CHARS.get(fmt, 50)
    chain = EXTRACTORS.get(fmt) or [("markitdown", _markitdown)]
    for name, fn in chain:
        text = _run_cli(name, src) if name in CLI_TOOLS else (fn(src) if fn else None)
        if text and len(text.strip()) >= floor:
            return text, name
    if fmt == "pdf":
        text = _pdf_pymupdf(src)
        if text:
            return text, "pymupdf(partial)"
    return None, "-"


# ---------------------------------------------------------------- 输入

def collect_inputs(raw_paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in raw_paths:
        p = Path(raw).expanduser()
        if p.is_dir():
            files.extend(sorted(f for f in p.rglob("*")
                                if f.is_file() and f.suffix.lower() in SUPPORTED))
        elif p.is_file():
            files.append(p)
        else:
            hits = [Path(h) for h in sorted(globmod.glob(raw, recursive=True))
                    if Path(h).is_file() and Path(h).suffix.lower() in SUPPORTED]
            if not hits:
                log(f"⚠️  未匹配到支持的文件: {raw}")
            files.extend(hits)
    seen, out = set(), []
    for f in files:
        r = f.resolve()
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


# ---------------------------------------------------------------- --check

def do_check() -> int:
    log("book-to-skill · 抽取器环境预检")
    log("=" * 62)
    log(f"Python: {sys.version.split()[0]}   {sys.executable}")
    log("")
    log(f"{'格式':<11}{'可用':<7}{'首选抽取器':<17}缺失时安装")
    log("-" * 62)
    py = sys.executable
    missing = False
    for fmt in sorted(EXTRACTORS):
        ok, name = extractor_status(fmt)
        inst = ""
        if not ok:
            missing = True
            pkg = INSTALL_HINT.get(fmt)
            inst = (f"uv pip install --python {py} {pkg}" if pkg
                    else "(无法自动安装)")
        log(f"{fmt:<11}{'✅' if ok else '❌':<7}{name:<17}{inst}")
    log("-" * 62)
    log("")
    if missing:
        log("⚠️  部分格式缺抽取器。装齐后重跑，或加 --install-missing yes。")
        return 1
    log("✅ 全部格式就绪")
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="extract.py",
        description="抽取书籍/文档正文 → full_text.txt + metadata.json")
    ap.add_argument("paths", nargs="*", help="文件 / 目录 / glob")
    ap.add_argument("--mode", choices=["text", "technical"], default="text")
    ap.add_argument("--install-missing", choices=["ask", "yes", "no"], default="ask")
    ap.add_argument("--check", action="store_true", help="只做环境预检，不抽取")
    ap.add_argument("--workdir", default=os.environ.get("BOOK_SKILL_WORKDIR", ""),
                    help="工作目录（默认随机临时目录）")
    args = ap.parse_args(argv)

    if args.check:
        return do_check()
    if not args.paths:
        log("用法: extract.py <path>... [--mode text|technical] [--install-missing ask|yes|no]")
        return 2

    files = collect_inputs(args.paths)
    if not files:
        log(f"❌ 未找到支持的文件。支持: {' '.join(sorted(SUPPORTED))}")
        return 1

    if args.install_missing == "ask":
        bad = sorted({f.suffix.lower().lstrip('.') for f in files
                      if not extractor_status(f.suffix.lower().lstrip('.'))[0]})
        if bad:
            log(f"⚠️  缺抽取器的格式: {', '.join(bad)}")
            if sys.stdin.isatty():
                ans = input("   自动安装缺失依赖? [y/N] ").strip().lower()
                if ans in ("y", "yes"):
                    args.install_missing = "yes"
    if args.install_missing == "yes":
        log(f"📦 安装: uv pip install --python {sys.executable} {' '.join(FALLBACK_PKGS)}")
        subprocess.run(["uv", "pip", "install", "--quiet",
                        "--python", sys.executable, *FALLBACK_PKGS])

    workdir = Path(args.workdir) if args.workdir else Path(
        tempfile.gettempdir()) / f"book_skill_work-{os.getpid()}-{int(time.time())}"
    workdir.mkdir(parents=True, exist_ok=True)

    log(f">>> 抽取 {len(files)} 个文件（mode={args.mode}）\n")
    sources, chunks, failures = [], [], []

    for f in files:
        fmt = f.suffix.lower().lstrip(".")
        ok, planned = extractor_status(fmt)
        log(f"  [{fmt:>8}] {f.name}  → {planned}")
        if not ok:
            failures.append({"file": str(f), "format": fmt, "error": "no extractor available"})
            log("             ❌ 无可用抽取器")
            continue
        text, used = extract_one(f, args.mode)
        if not text:
            failures.append({"file": str(f), "format": fmt,
                             "error": "no text extracted (scanned/image PDF needs OCR)"})
            log("             ❌ 抽取失败（可能是扫描件，需 OCR）")
            continue
        tok = estimate_tokens(text)
        sources.append({
            "filename": f.name, "source_file": str(f), "format": fmt,
            "extractor": used, "chars": len(text),
            "words": len(text.split()), "estimated_tokens": tok})
        log(f"             ✅ {used}  {len(text):,} 字符  ~{tok:,} token")
        chunks.append(f"{'=' * 78}\nSOURCE: {f}\nFORMAT: {fmt}  EXTRACTOR: {used}\n"
                      f"{'=' * 78}\n\n{text.strip()}")

    full_text = "\n\n\n".join(chunks) if chunks else ""
    if not full_text:
        log("\n❌ 所有源都抽取失败，未生成 full_text.txt")
        return 1

    text_path = workdir / "full_text.txt"
    text_path.write_text(full_text, encoding="utf-8")
    total_tok = estimate_tokens(full_text)

    meta = {
        "workdir": str(workdir), "text_file": str(text_path), "mode": args.mode,
        "total_sources": len(sources), "failed_sources": len(failures),
        "combined_chars": len(full_text), "combined_words": len(full_text.split()),
        "estimated_tokens": total_tok, "images_dropped": 0,
        "sources": sources, "failures": failures,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    meta_path = workdir / "metadata.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    log("")
    log(f"📖 Sources extracted: {len(sources)}/{len(files)}"
        + (f"（{len(failures)} 个失败）" if failures else ""))
    log(f"📄 Combined words: ~{meta['combined_words']:,} | Tokens: ~{human(total_tok)}")
    log("")
    log(f"Workdir -> {workdir}")
    log(f"Text    -> {text_path}")
    log(f"Meta    -> {meta_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())