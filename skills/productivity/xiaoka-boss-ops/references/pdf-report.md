---
name: report-pdf
description: Use when generating PDF reports from Chinese markdown. Converts Obsidian-style MD to styled PDF via weasyprint, with CJK font handling, page numbers, and code-block wrapping.
---

# 中文 Markdown → PDF 报告

## 环境（已装）
- 引擎：`weasyprint` 70.0，在 `/opt/data/.venv-browser` venv 里
- 用 `uv pip install --python /opt/data/.venv-browser/bin/python <pkg>`（**venv 里没有 pip**，`python -m pip` 会失败）
- 中文字体：`WenQuanYi Zen Hei`（`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`），系统只有 7 个中文字体，**不要用 font-family 假设有 Noto/思源**
- 无 pandoc / wkhtmltopdf / LaTeX

## 核心坑

### 1. 中文必须显式声明 font-family
系统默认字体渲染不出中文（豆腐块）。必须在 CSS 里写：
```css
body { font-family: "WenQuanYi Zen Hei", "Unifont-JP", sans-serif; }
```

### 2. `<pre>` 里的长行会溢出
Prompt 代码块经常一行 100+ 字。必须：
```css
pre { white-space: pre-wrap; word-break: break-all; }
code { word-break: break-all; }
```
否则右侧内容被裁掉。

### 3. Markdown → HTML 要自己写
没有 pandoc。用 `markdown` 包或手写转换。weasyprint 只吃 HTML。

### 4. Emoji 在 Zen Hei 里没有
`👍💬🎯` 会变豆腐块。要么替换成文字（`[赞]`），要么注册 DejaVu Sans 作为 fallback。

## 模板 CSS（实测可用）

```css
@page {
  size: A4;
  margin: 18mm 16mm 16mm;
  @bottom-center {
    content: counter(page) " / " counter(pages);
    font-size: 8pt; color: #888;
    font-family: "WenQuanYi Zen Hei", sans-serif;
  }
}
body {
  font-family: "WenQuanYi Zen Hei", "DejaVu Sans", sans-serif;
  font-size: 10.5pt; line-height: 1.75; color: #1a1a1a;
  h1 { font-size: 20pt; color: #0f4c81; border-bottom: 2.5pt solid #0f4c81;
       padding-bottom: 5pt; margin: 0 0 12pt; }
  h2 { font-size: 14pt; color: #0f4c81; border-left: 3.5pt solid #0f4c81;
       padding-left: 8pt; margin: 16pt 0 8pt; page-break-after: avoid; }
  h3 { font-size: 11.5pt; color: #2c5f8a; margin: 11pt 0 5pt; page-break-after: avoid; }
  pre { background: #f5f7fa; border: 0.5pt solid #d5dae0; border-left: 3pt solid #0f4c81;
        padding: 8pt 10pt; white-space: pre-wrap; word-break: break-all;
        font-size: 8.8pt; line-height: 1.5; font-family: "DejaVu Sans Mono", monospace;
        page-break-inside: avoid; }
  blockquote { border-left: 3pt solid #f0a030; background: #fff9f0;
               padding: 6pt 12pt; margin: 8pt 0; color: #5a4a30; }
  table { border-collapse: collapse; width: 100%; font-size: 9.2pt;
          page-break-inside: avoid; }
  th { background: #0f4c81; color: #fff; padding: 5pt 7pt; text-align: left; }
  td { border: 0.5pt solid #d5dae0; padding: 4pt 7pt; }
  tr:nth-child(even) td { background: #f7f9fb; }
```

## 标准流程

```python
import markdown, weasyprint
html_body = markdown.markdown(md_text, extensions=['tables','fenced_code','toc'])
weasyprint.HTML(string=f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html_body}</body></html>"
                ).write_pdf(out_path)
```

## 交付
- PDF 写本地 scratch，**不要直接写 NAS**（write_file 有 HERMES_WRITE_SAFE_ROOT 限制）
- 需要给用户看就上传到 vault 或用 MEDIA: 路径