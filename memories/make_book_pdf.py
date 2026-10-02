#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小卡 · 生成《WorkBuddy + 知识星球做课赚钱手册》精读 PDF 报告
用法: python3 make_book_pdf.py
输出: /opt/data/cache/scratch/WorkBuddy做课手册-精读报告.pdf
"""
import os, re, markdown, weasyprint

SCRATCH = "/opt/data/cache/scratch"
BOOK = ("/opt/nas/volume2/2-AI/obsidian_vault/12-知识星球/Workbuddy一人公司营/2026-09/"
        "【手机号】454152 - WorkBuddy + 知识星球：一个人自动化的做课赚钱手册.md")
CH07_11 = "/opt/data/output/WorkBuddy知识星球-第07-11章实战笔记.md"
OUT = os.path.join(SCRATCH, "WorkBuddy做课手册-精读报告.pdf")

CSS = """@page {
  size: A4; margin: 17mm 15mm 15mm;
  @bottom-center { content: counter(page) " / " counter(pages);
    font-size: 8pt; color: #9aa4ae; font-family: "WenQuanYi Zen Hei", sans-serif; }
  @top-right { content: "WorkBuddy 做课赚钱手册 · 精读报告";
    font-size: 7.5pt; color: #b8c0c8; font-family: "WenQuanYi Zen Hei", sans-serif; }
}
body { font-family: "WenQuanYi Zen Hei", "DejaVu Sans", sans-serif;
  font-size: 10.2pt; line-height: 1.72; color: #1c2024; }
h1 { font-size: 19pt; color: #0d4f7d; border-bottom: 2.5pt solid #0d4f7d;
  padding-bottom: 6pt; margin: 4pt 0 14pt; page-break-before: always; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-size: 13.5pt; color: #0d4f7d; border-left: 3.5pt solid #0d4f7d;
  padding-left: 8pt; margin: 15pt 0 7pt; page-break-after: avoid; }
h3 { font-size: 11.2pt; color: #2a6088; margin: 10pt 0 4pt; page-break-after: avoid; }
h4 { font-size: 10.2pt; color: #4a5560; margin: 8pt 0 3pt; page-break-after: avoid; }
p { margin: 4pt 0; text-align: justify; }
pre { background: #f4f7fa; border: 0.5pt solid #d3dae1; border-left: 3pt solid #0d4f7d;
  padding: 7pt 9pt; white-space: pre-wrap; word-break: break-all; font-size: 8.2pt;
  line-height: 1.45; font-family: "DejaVu Sans Mono", monospace;
  page-break-inside: avoid; margin: 6pt 0; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8.8pt;
  background: #eef2f6; padding: 0.5pt 2pt; border-radius: 2pt; word-break: break-all; }
blockquote { border-left: 3pt solid #e8a33d; background: #fff9f0;
  padding: 6pt 11pt; margin: 7pt 0; color: #57482e; page-break-inside: avoid; }
blockquote p { margin: 2pt 0; }
table { border-collapse: collapse; width: 100%; font-size: 8.8pt;
  margin: 7pt 0; page-break-inside: avoid; }
th { background: #0d4f7d; color: #fff; padding: 4.5pt 6pt; text-align: left;
  font-weight: normal; }
td { border: 0.5pt solid #d3dae1; padding: 3.5pt 6pt; vertical-align: top; }
tr:nth-child(even) td { background: #f6f9fb; }
ul, ol { margin: 4pt 0 4pt 16pt; padding: 0; }
li { margin: 2pt 0; }
hr { border: none; border-top: 0.5pt solid #d3dae1; margin: 10pt 0; }
strong { color: #0d4f7d; }
.cover { text-align: center; padding-top: 45mm; page-break-after: always; }
.cover h1 { border: none; font-size: 26pt; color: #0d4f7d; margin: 0 0 6pt;
  page-break-before: avoid; }
.cover .sub { font-size: 13pt; color: #5a6570; margin: 4pt 0; }
.cover .meta { font-size: 10pt; color: #8b95a0; margin-top: 22pt; line-height: 1.9; }
.toc li { margin: 3pt 0; font-size: 10pt; }
"""


def build():
    parts = []

    # ---------- 封面 ----------
    parts.append("""<div class="cover">
<h1>WorkBuddy + 知识星球</h1>
<div class="sub">一个人自动化的做课赚钱手册</div>
<div class="sub">全 11 章精读报告</div>
<div class="meta">
原文：49,457 字 / 11 章 / 知识星球 group 88884585518442<br>
作者：袁六伟 ｜ 原文时间：2026-09-14<br>
精读整理：小卡（xiaoka）｜ 报告日期：2026-10-02<br>
<span style="color:#b0b8c0">依据库内原文逐章提炼，未编造内容</span>
</div>
</div>""")

    # ---------- 阅读说明 ----------
    parts.append("""# 阅读说明与核心结论

## 这份报告是什么

对知识星球文章《WorkBuddy + 知识星球：一个人自动化的做课赚钱手册》（袁六伟，2026-09-14，全文 49,457 字 / 11 章）的逐章精读整理。内容全部来自库内原文，**没有编造，没有空话总结**。

## 作者开篇的两句真话（原话照录）

> 「书里的价格和销量是我的真实轨迹，不是给你的建议价。」
> 「带『示意』字样的段落是为讲清方法举的典型场景，不是某个具体学员。」

## 全书一句话

**做课不是写课，是倒着做。** 先想清楚谁会掏钱 → 出标题 → 写详情页 → 写大纲和逐字稿。顺序错了，课做得再好也没人点。

## 九环流水线

`定位 → 标题 → 详情页 → 大纲与逐字稿 → 发售 → 活动 → 内容 → 上星球 → 复盘`

前一环的输出是后一环的输入。定位没定，标题只能靠形容词堆。**多数人只卡一环，不是「不会做课」。**

## 作者真实数据（原话照录）

| 指标 | 数值 | 口径 |
|---|---|---|
| 一人公司实战课累计交付 | 1,600+ 份 | 付费人数 |
| 三条线（课/陪跑营/商单）流水 | 约 200,000 元 | 流水，非净利 |
| 商单客户 | 100+ | 客户数 |
| 学员总数 | 6,000+ | 累计 |
| 50 元档（8/4–8/31） | 1,498 人 / ¥74,900 | 真实成交 |
| 99 元档（9/1–9/14） | 274 人 / ¥26,829 | 真实成交 |

**涨价后他自己算的账**：客单价翻倍，但日均新增从 53.5 人/天掉到 19.4 人/天，日均流水从 ¥2,675/天掉到 ¥1,916/天。

**他明确写出的核验边界**（防止案例被读歪）：
1. 两期长度不同（28 天 vs 14 天），可用日均拉平长度，但**拉不平行情** —— 不能讲成「涨价导致需求崩了」
2. 这是两次定价期的**横截对比，不是一条时间曲线**，**不许写成「趋势下滑」**
3. 涨价不是为了逼单，是为了**把人分层**；50 元档的交付是 99 元档能站住的底

## 模式选择规律（作者反复提到的操作细节）

| 模式 | 用途 | 典型场景 |
|---|---|---|
| **Plan** | 需要你先拍板、不许它动手 | 流水线地图、大纲总表 |
| **Ask** | 需要它拷问你、逼你说明白 | 课程定位三问 |
| **Agent** | 已经想清楚、直接落文件 | 详情页、逐字稿、发售节奏表、话术包 |

## 目录

- 第 01 章 · 先看整条流水线：做课不是写课
- 第 02 章 · 定位：先想清楚谁会掏钱
- 第 03 章 · 标题工厂：一次出 20 个，再打分选 3 个
- 第 04 章 · 详情页：把「怕学不会」一条条堵掉
- 第 05 章 · 大纲与逐字稿：把课做成能交付的成品
- 第 06 章 · 发售：先收一笔钱，再做完整门课
- 第 07 章 · 活动运营：把买过课的人变成交作业的人
- 第 08 章 · 内容运营：星球天天有得看
- 第 09 章 · 社群承接：新人 24 小时和每天巡场
- 第 10 章 · 把课搬进星球：连接、发布、专栏、改稿
- 第 11 章 · 复盘 + 90 天
- 跨章硬约束汇总""")

    # ---------- 第 01-06 章 ----------
    p1 = os.path.join(SCRATCH, "wb_part1.md")
    parts.append(open(p1, encoding="utf-8").read() if os.path.exists(p1)
                 else "# 第 01-06 章\n\n> 提取失败。\n")

    # ---------- 第 07-11 章实战笔记（子agent 落盘文件）----------
    if os.path.exists(CH07_11):
        t = open(CH07_11, encoding="utf-8").read()
        # 去掉它自己的 h1 标题（避免与目录重复）
        t = re.sub(r'^#\s+WorkBuddy.*?\n', '', t, count=1, flags=re.S)
        parts.append("# 第 07–11 章 · 实战笔记\n\n" + t.strip())
    else:
        parts.append("# 第 07–11 章 · 实战笔记\n\n> 子 agent 落盘文件缺失。")

    # ---------- 渲染 ----------
    md_all = "\n\n".join(parts)
    body = markdown.markdown(md_all, extensions=["tables", "fenced_code", "toc", "attr_list"])
    html = ("<html><head><meta charset='utf-8'><title>WorkBuddy 做课手册 精读报告</title>"
            f"<style>{CSS}</style></head><body>{body}</body></html>")
    weasyprint.HTML(string=html).write_pdf(OUT)
    return OUT


if __name__ == "__main__":
    out = build()
    print(f"PDF 生成: {out} ({os.path.getsize(out):,} 字节)")
    try:
        from pypdf import PdfReader
        r = PdfReader(out)
        print(f"页数: {len(r.pages)}")
        t = r.pages[0].extract_text()[:200]
        print(f"首页文本: {t[:150]}")
    except Exception as e:
        print(f"校验: {e}")