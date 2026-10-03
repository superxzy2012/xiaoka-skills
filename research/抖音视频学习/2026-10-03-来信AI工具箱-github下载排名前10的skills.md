---
title: 来信AI工具箱 - github下载排名前10的skills（图文）
source: https://v.douyin.com/qAqAUyRTJVs/
author: 来信AI工具箱
date: 2026-10-03
type: 抖音图文
tags: [技能发现, skills.sh, 开源复用, 核查纠错]
status: 已核查
---

# 来信AI工具箱：github下载排名前10的skills

> 原文标题：「github下载排名前10的skills。适合新人」
> 作者：来信AI工具箱
> 核验日期：2026-10-03（原文标注 2026.09.03）

## ⚠️ 核查结论：有硬伤

**结论：技能本身是真的，但排名和数字全错。**

### 问题 1：标题误导 —— 这不是 GitHub Stars 榜

原图写「按 GitHub Stars 排序」，但列出的数字是 **skills.sh 平台的安装次数**
（`320万次安装` / `69.5万次安装`），和 GitHub Stars 完全两码事。

实测差距（视频数字 ÷ 真实 Stars）：

| 技能 | 视频「安装次数」 | 真实 GitHub Stars | 倍数 |
|---|---|---|---|
| frontend-design | 3,200,000 | 1,164 | 2749× |
| find-skills | 695,000 | 341 | 2038× |
| grill-me | 683,000 | 765 | 893× |
| vercel-react-best-practices | 637,000 | 6 | 106167× |
| agent-browser | 779,000 | 43,468 | 18× |
| tdd | 854,000 | 2,778 | 307× |
| microsoft-foundry | 599,000 | 2,573 | 233× |

### 问题 2：数字与 skills.sh 当前实际数据不符

| 技能 | 视频 | 实际榜位 · 安装数 |
|---|---|---|
| find-skills | 69.5万 | **#1 · 3.7M** |
| grill-me | 68.3万 | #2 · 1.3M |
| frontend-design | **320万** | **#7 · 948.5K** |
| tdd | 85.4万 | #6 · 1.0M |
| microsoft-foundry | 59.9万 | **#58** · 628.2K |
| web-design-guidelines | — | #45 · 694.1K |

视频称 frontend-design 320 万排第一；实际 94.85 万、排第 7。

### 问题 3：榜单本身选错

漏掉真榜上的 `setup-matt-pocock-skills`(930.4K)、`hyperframes-cli`(772.5K)，
却塞进排 #58 的 microsoft-foundry 和 #45 的 web-design-guidelines。

## ✅ 真实 Top 10（2026-10-03 抓自 skills.sh）

| # | 技能 | 安装数 | 仓库 |
|---|---|---|---|
| 1 | find-skills | 3.7M | vercel-labs/skills |
| 2 | grill-me | 1.3M | mattpocock/skills |
| 3 | grill-with-docs | 1.1M | mattpocock/skills |
| 4 | improve-codebase-architecture | 1.0M | mattpocock/skills |
| 5 | agent-browser | 1.0M | vercel-labs/agent-browser |
| 6 | tdd | 1.0M | mattpocock/skills |
| 7 | frontend-design | 948.5K | anthropics/skills |
| 8 | setup-matt-pocock-skills | 930.4K | mattpocock/skills |
| 13 | hyperframes-cli | 772.5K | heygen-com/hyperframes |
| 14 | vercel-react-best-practices | 766.5K | vercel-labs/agent-skills |

**2-8 名里 6 个出自 mattpocock 一人之手** —— 该作者技能质量确实高。

## 📦 实际安装（2026-10-03）

本机原本已有 6/10：`find-skills`、`grill-me`、`vercel-react-best-practices`、
`agent-browser`、`tdd`、`microsoft-foundry`。

补装 2 个（均为 MIT）：

| 技能 | 来源 | 许可 | 内容 |
|---|---|---|---|
| `frontend-design` | anthropics/skills | MIT + LICENSE.txt | 9,363 字符，反模板化视觉设计 |
| `domain-modeling` | mattpocock/skills | MIT | ADR-FORMAT.md + GLOSSARY-FORMAT.md + agents/ |

**关于 `grill-with-docs`：不装。** 该 SKILL.md 仅 247 字节，正文只写
「Call the Skill tool twice, for "grilling" and "domain-modeling"」——
它是个组合器，本身无内容。它调用的 `domain-modeling` 已装；
`grilling` 本机已有（名为 `grill-me` / `grilling`）。

## 🔑 可迁移的方法论

> 原文核心启发：「Skill 的价值，不只是多一个功能，而是把稳定的方法变成 AI 每次都能照着执行的流程。」
> 选装建议：「先问自己最常做的任务，只装能补上缺口的 Skill。」

这与本机 `find-skills-xiaoka` 的纪律一致：不按榜单装，按缺口装。

## 🔗 相关

- 技能：`/opt/data/skills/frontend-design/`、`/opt/data/skills/domain-modeling/`
- 共享库：`/opt/nas/volume2/2-AI/skills/{frontend-design,domain-modeling}`
- 榜单原始数据：`/opt/data/cache/scratch/skills_sh_top.json`（185 条）
- OCR 脚本：`/opt/data/cache/scratch/parse_top.py`
- 参见：`15-小卡工作区/学习输出/开源调研/GitHub高星开源清单-Ozon美客多-20261002.md`