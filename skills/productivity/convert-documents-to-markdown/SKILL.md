---
name: convert-documents-to-markdown
description: Convert Word/PPT/Excel/RTF/EPUB/PDF docs to Markdown.
license: MIT
version: 1.0.0
metadata:
  author: firecrawl
  source: https://github.com/firecrawl/anydoc (★22,472)
  installed_by: 小卡 2026-10-04
  hermes:
    tags: [document, markdown, office, pdf, conversion]
    related_skills: [markitdown-skill, pdf-processor-cn, book-note-taking]
---

# Convert documents to Markdown

把办公文档转成干净的 GitHub-Flavored Markdown。用在 read_file / markitdown 读不了
office 文档的场景（Word 表格、PPT 版式、Excel 公式格、PDF 排版）。

**为什么不用 markitdown**：格式覆盖更全（含 OpenDocument/RTF/EPUB/CSV），
Rust 内核快一个量级，且格式识别看真实内容而非扩展名。

## When to Use

- BOSS 发来 office 文档（.docx/.pptx/.xlsx/.odt/.rtf/.epub）而 read_file 读不出内容
- PDF 有复杂排版/表格，需要转 Markdown 做分析或入库
- 需要把办公文档喂给 agent（统一成一种 GFM 结构，模型只需学一种）
- **不要用**：纯扫描件/图片型 PDF（anydoc 不做 OCR，走 `--ocr hosted` 或 `rapidocr_onnxruntime`）

## 用法

```bash
npx -y @firecrawl/anydoc <file>               # Markdown to stdout
npx -y @firecrawl/anydoc <file> -o out.md     # 写文件
npx -y @firecrawl/anydoc - --format csv < f   # 从 stdin 读
```

Node 20+ 必需（本机 v26.5.1 ✅）。无需 install —— `npx` 拉预编译二进制，
首次约 7 秒，之后约 2 秒。

## 规则

1. **支持格式**：`.doc .docx .docm .odt .rtf .epub .pdf .ppt .pps .pot .pptx .pptm .ppsx .ppsm .odp .xls .xlsx .xlsm .xlsb .ods .csv`
2. **格式从文件内容识别，不看扩展名**（实测：docx 改名成 .txt 照样正确解析）。
   只在检测失败时传 `--format`：stdin 里的 CSV，或扩展名缺失/写错时。
3. **Exit codes**：`0` 成功 / `1` 无法转换 / `2` 用法错误 / `3` PDF 有页面需 OCR。
   失败时 stderr 打印一行 `anydoc: <message>`。CLI 不交互、不提示。
4. **大文档用 `-o` 写文件**，再只读需要的部分 —— 不要把全文流进 context。
5. **扫描件/纯图片页 anydoc 自己不做 OCR**，会 exit 3。加 `--ocr hosted` 交给
   [Firecrawl Parse](https://firecrawl.dev/parse)（免注册；`--api-key` 或
   `FIRECRAWL_API_KEY` 可提额度）。
6. **在 Node/Python/Rust 代码库里优先用库**：`@firecrawl/anydoc`(npm) /
   `firecrawl-anydoc`(PyPI) / `anydoc`(crates.io)，均导出 `to_markdown` / `toMarkdown`。

## 本机已实测（2026-10-04）

| 验证项 | 结果 |
|---|---|
| CSV → GFM 表格 | ✅ 表头分隔行正确 |
| docx 表格 | ✅ 正确转成 GFM 管道表 |
| docx Heading1 样式 | ✅ 输出 `# 标题`（**前提：docx 内含 `word/styles.xml`**，缺了样式无从解析） |
| 改扩展名骗它 | ✅ docx→.txt 仍正确识别 |
| 伪装成 docx 的垃圾文件 | ✅ exit 1 + `not a readable zip archive` |

## 与本机其他文档工具的选型

| 工具 | 适用 |
|---|---|
| **本技能 (anydoc)** | 办公文档 → Markdown，格式覆盖最全，Rust 内核快 |
| `pdf-processor-cn` | PDF 深度问答、渲染成图片 |
| `markitdown-skill` | 微软官方，同类用途，作备选 |
| `book-note-taking` | PDF 书 → 结构化笔记 → Obsidian |

扫描件走 `--ocr hosted`；纯本地 OCR 用 `rapidocr_onnxruntime`（装在 `/opt/data/.venv-browser`）。

## 坑

- `npm notice` 会混进 stdout，过滤：`grep -v "^npm notice"`
- 本机无 `zip` 命令、无 `python-docx`；造 Office 测试文件用 Python `zipfile` 直接写 OOXML
- 建 fixture 时**别漏 `styles.xml`**，否则标题样式测不出来（会误判成工具不识别样式）
