---
name: deepread-report-pipeline
description: Use when deep-reading a long source into a report.
version: 1.0.0
author: 小卡 (Hermes)
license: MIT
agent_created: true
metadata:
  hermes:
    tags: [PDF, 报告, 精读, Obsidian, 验收]
    related_skills: [obsidian, xiaoka-boss-ops]
---

# 长文精读报告流水线

把「库里已有一篇长文 → 产出一份可直接执行的结构化报告（PDF + 归档）」做成确定性流水线。

## When to Use

- 「完整精读这篇手册，给我 PDF 报告」
- 「把这个知识星球作者的系列文章总结一下」
- 「这本书/这套课程，出一份能落地的实战笔记」
- 任何**源文件已在库里、目标是一份交付级报告**的任务

不适用：单篇文章摘要、只需口头结论的问答、纯翻译。

## 铁律（不可协商）

1. **只认 canonical source。** 一份一份往下翻目录统计出来的「总结」不是原文。精读前先按字符量筛出**信息密度最高的单文件**（正文 4 万字以上、章节齐全、Prompt 完整），以它为准。目录统计只用来确认「有没有遗漏」。
2. **原文自带的可复制资产必须字节级照抄。** Prompt、模板、字段表、阈值表 —— 一律**用结构标记从原文机械抽取**（见步骤 3），绝不让模型重新打一遍。重新打字是这类任务里最大的失真来源：改一个标点、少一行约束、漏一个禁止项，下游全部跑偏。
3. **区分「原文事实」与「示意」边界。** 源文里标注为示意/举例/待确认的内容，报告里必须原样保留标注。真实业绩数字要带口径与来源。凭空补一个「典型学员案例」就是造假。
4. **报告不是章节复述。** 每章给的是「为什么这么做」，可直接粘的资产，列表化的阈值，以及作者原话形式的坑（保留原话是因为原话就是最清晰的规则陈述）。
5. **不编造，读到什么写什么。** 某章确实短就如实说明短在哪，不要用空话把长度补齐。

## 流程

### 1. 锁 canonical source

```bash
python3 - <<'EOF'
import glob
for f in sorted(glob.glob('/opt/nas/volume2/2-AI/obsidian_vault/**/*.md', recursive=True)):
    n = len(open(f, encoding='utf-8', errors='ignore').read())
    if n > 30000: print(f"{n:>7}  {f}")
EOF
```

拿到文件后先切章节并核对字数，确认没有缺章：

```python
import re
txt = open(path, encoding='utf-8').read()
heads = [(m.start(), m.group()) for m in re.finditer(r'第[零一二三四五六七八九十\d]+章[^\n]*', txt)]
for (a, t), (b, _) in zip(heads, heads[1:]):
    print(f"{t}  -> {b-a} 字符")
```

切出长度略高于文末声明字数是正常的（跨章引用 + 重复末句），不要误判为缺字。

### 2. 并行精读（可选，但有前提）

长文（>3 万字）单次线性读必漏 Prompt 和阈值。可按章拆给多个子 agent。

**前提：每个子 agent 必须把成果写入指定文件，并回报绝对路径。**

```bash
# 在派发指令里写死这句
"输出要求：把完整成果写入 /opt/data/output/<name>.md，
 并在最终回复里给出该文件的绝对路径和字节数。"
```

**为什么**：子 agent 的 summary 是自述，不是产物。只在返回体里、不落盘的成果，等于没有 —— 后续合并时既无法校验，也无法在上下文压缩后恢复。文件存在 + 字节数是唯一可验证的交付凭据。

**合并前先验证**：

```bash
ls -la /opt/data/output/*.md   # 每个都必须在且非空
```

若有缺失：**不要凭 summary 重建**，直接回 canonical source 重新抽取那部分。summary 里的转述已经过一手压缩，正是最容易丢 Prompt 的环节。

### 3. 机械抽取原文资产

先探测资产的边界标记，再批量切：

```python
import re, json
txt = open(path, encoding='utf-8').read()
for mark in ["【角色】", "【禁止】", "Prompt"]:
    print(mark, txt.count(mark))

starts = [m.start() for m in re.finditer(r'【角色】', txt)]
blocks = []
for i, s in enumerate(starts):
    e = txt.find('【禁止】', s)
    e = txt.find('\n\n', e) if e > 0 else (starts[i+1] if i+1 < len(starts) else len(txt))
    blocks.append(txt[s:e])
json.dump(blocks, open('/opt/data/cache/scratch/assets.json', 'w'), ensure_ascii=False)
```

先打印每块的前 120 字人工核对边界，再灌进报告。**边界错了会静默串章** —— 少一个尾标记就吞掉下一段开头。

给每个块补元信息（来自哪一章、什么模式、产出什么文件），资产才可被复用，而不只是可读：

```python
meta = [("第 01 章", "流水线地图", "Plan", "我的-流水线地图.md"), ...]
```

### 4. 组装报告

按「速查表 → 核心逻辑 → 关键阈值 → 原文资产 → 坑 → 交付物清单」组织，不要按章节顺序平铺。

**改大段缩进代码时优先用程序化切片替换，不要用 `patch` 重打缩进** —— `patch` 的模糊匹配对缩进敏感，手打的新块常常丢失前导空格导致语法错误。`execute_code` 里 `s[:start] + new + s[end:]` 再 `py_compile` 验证更稳。

### 5. 渲染 + 验收

WeasyPrint / CSS / CJK 字体等**渲染**细节不在本 skill，在 `xiaoka-boss-ops`（另一个 skill）的 `references/pdf-report.md`，含实测可用的 CSS 骨架与中文 Markdown→HTML 步骤。本 skill 只管内容正确性与验收。

**验收门禁必跑** → 用本 skill 自带脚本：

```bash
python3 scripts/verify_pdf.py 报告.pdf \
  --keywords "定位" "详情页" "复盘" "90 天" \
  --probes "每个资产的唯一特征串" \
  --out /opt/data/cache/scratch/pdf_text.txt
```

六项硬门槛全过才交付：内嵌字体 / 无乱码 / 无正文溢出 / 右边距 / 关键词覆盖 / 书签。
详细判据与「验收脚本自己骗自己」的三个坑见 `references/verification-gates.md`。

**没有 vision provider 时不要声称「已目检」**，用几何校验 + 文本抽取代替，并在交付说明里如实写明验收方式。

### 6. 归档三件套

```
<vault>/15-小卡工作区/学习输出/
  <名>_YYYYMMDD.pdf
  <名>_全文文本_YYYYMMDD.md     # 从 PDF 抽的，Obsidian vault 内可搜
  <名>_索引_YYYYMMDD.md          # frontmatter + 双链回源文件 + 核心结论
```

- 索引笔记 frontmatter 用 `source_file:` 双链回 canonical source，`pdf:` 双链回 PDF —— 这是以后能在库里反查的唯一线索。
- `md5sum` 对比源文件与 NAS 副本，确认 cp 完整。
- 索引里同时列：核心结论若干条、资产清单表、原文的真实数据（标口径）、作者明说拿不到的数据（避免下游误造指标）。

## 交付时给什么

- 结论先行的短摘要 + 一张验收结果表（页数/字体/关键词/资产/敏感串，各一行）
- 最值钱的 3–5 条提炼
- 归档路径
- **一个具体的下一步**，不要用「还需要我做什么」收尾

## 常见失败模式

| 现象 | 原因 | 解法 |
|---|---|---|
| 报告里 Prompt 少了一截约束 | 模型重新打字时丢行 | 机械抽取，字节照抄 |
| 章节内容其实来自目录碎片 | 没锁 canonical source | 步骤 1 按字符量筛 |
| 子 agent 成果无处可查 | 没要求落盘 | 派发时写死输出路径 + 字节数 |
| 验收脚本报全页乱码 | 判据写成了空串，恒真 | 用真字符 U+FFFD |
| 验收脚本报每页都越界 | 页脚页码在页底，被算进溢出 | 先剔 y0 > 页高-40 的页脚带 |
| 下游据此伪造了互动率指标 | 源文明说接口拿不到 | 报告里单列「数据限制」段 |