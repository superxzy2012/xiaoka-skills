---
title: 让你告别不会写AI提示词 — prompt-optimizer
source: https://v.douyin.com/wz-xHjY-hMY/
douyin_id: "7690952210615782682"
author: V哥AI搞米有东西
date: 2026-10-03
type: 抖音视频
duration: 30s
tags: [提示词工程, prompt-optimizer, 文生图, 开源项目, AGPL]
status: 已核查
project: linshenkx/prompt-optimizer
---

# 让你告别不会写 AI 提示词 —— prompt-optimizer

> 🎬 抖音 · V哥AI搞米有东西 · 30秒 · 2026-10-03 入库

## 📝 转录原文（cloud/turbo）

> 最近看到一个非常实用的开源项目他在 GitHub 已经拿下了 36K 的 Star
> 他的工作就是帮你写好提示词
> 你只需要把一个模糊想法敲进去几秒钟他就能给你生成一条有结构有措辞的专业提示词
> 最夸张的是他还支持文生图 图生图的提示词一键优化
> 想生成的画面说不清楚 他能帮你翻译成模型听得懂的语言
> 甚至他还支持提示词对比 优化前和优化后 定牌摆出来差别肉眼可见
> 改没改对 当场验货就非常夸张

## 🎯 项目核实（2026-10-03，GitHub API 实测）

| 项 | 值 |
|---|---|
| 仓库 | **`linshenkx/prompt-optimizer`** |
| Stars | **36,180** ✅ 视频说36K，准确 |
| Forks | 4,183 |
| License | **AGPL-3.0** ⚠️ |
| 语言 | TypeScript |
| 创建 | 2025-02-12 |
| 最近 push | 2026-09-24 |
| 默认分支 | `develop`（非 main） |
| 最新 release | `v2.11.10`（2026-09-11） |
| 在线版 | https://prompt.always200.com |
| Chrome 商店 | `cakkkhboolfnadechdlgdcnjammejlna` |
| 部署方式 | Web / 桌面应用 / Chrome 扩展 / Docker / Vercel / Cloudflare Pages / MCP Server |

⚠️ **许可证坑**：GitHub API 报 `NOASSERTION`，因为它的 LICENSE 文件开头加了
「This program is licensed under the GNU Affero General Public License v3.0 only.」
这段自定义措辞导致 SPDX 识别失败。**实际就是 AGPL-3.0**，README badge 也写 AGPL-3.0。

## 🔍 视频 4 个说法逐条核实

| 视频说法 | 核实结果 |
|---|---|
| 「GitHub 拿下 36K Star」 | ✅ 准确，实测 36,180 |
| 「把模糊想法敲进去，生成有结构有措辞的专业提示词」 | ✅ 属实，官方 demo 明确展示"一句话 → 结构化提示词" |
| 「支持文生图、图生图的提示词一键优化」 | ✅ 属实，且比视频说的更多 |
| 「支持提示词对比，优化前后并排，差别肉眼可见」 | ✅ 属实，官方特性列表有"Analysis and Compare Evaluation" |

**结论：视频内容属实，无夸大。**

## 📌 官方完整功能（README 实测）

**四种使用方式**：Web 应用、桌面应用、Chrome 扩展、Docker 部署。

**核心能力**：
- **智能优化** —— 一键优化，支持多轮迭代改进
- **双模式** —— 系统提示词优化 + 用户提示词优化
- **分析对比评估** —— 分析、单结果评估、多结果对比评估
- **多模型集成** —— OpenAI、Gemini、DeepSeek、Grok、智谱 AI、SiliconFlow、MiniMax 等
- **Function Calling** —— 支持 OpenAI 和 Gemini 工具调用
- **纯客户端处理** —— 数据直连 AI 服务商，绕过中间服务器
- **访问控制** —— 密码保护功能

**图像生成模式**（超出视频描述）：
- 文生图（T2I）
- 图生图（I2I）—— 基于本地文件转换优化
- **多图生成** —— 多张输入图约束主体关系、顺序语义和最终生成目标
- 多模型支持 —— Gemini、Seedream、Grok
- **风格迁移** —— 从参考图学习风格、构图、色彩
- 预览下载、模型专属参数配置（尺寸、风格等）

**官方三个 demo 场景**（README 原文）：
1. **Hard-Nosed Reviewer** —— 从极简英文角色提示词出发，让小模型产出有结构的审查意见
2. **Marketplace Bargaining Reply** —— 单一模板 + 变量（商品细节、价格锚点、买家出价、语气、谈判目标），
   优化后同一小模型能写出更「可成交」的回复
2. **Text-to-Image** —— 一句话（"夜空中的悬浮图书馆"）优化成可直接控制的关键视觉提示词

## ⚠️ 与本机同名技能的区别（重要）

本机共享库**已有** `prompt-optimizer` 技能，但**完全是两回事**：

| | 本机版 | GitHub 版 |
|---|---|---|
| 位置 | `/opt/nas/volume2/2-AI/skills/prompt-optimizer/` | `linshenkx/prompt-optimizer` |
| 形态 | 纯 Markdown 提示词模板 | TypeScript Web/桌面/扩展应用 |
| 用途 | 把模糊表达改写成结构化任务（任务澄清） | 优化送给模型的提示词（提示词工程） |
| 来源 | 本机自建（WorkBuddy AURORA 05 工作流） | 开源，36,180★ |

**两者可互补**：本机版管「你要做什么」任务定义，GitHub 版管「怎么问模型」。
建议保留本机版（离线、无依赖、任务导向），GitHub 版作为**在线工具**用，不装为本机技能。

## 💡 值得关注的点

1. **纯客户端架构** —— 数据直连模型服务商，不过中间服务器。隐私上比多数同类工具好
2. **多模型自由切换** —— 同一提示词横向比多个模型输出，接近本机 `sealeap-skill-template`
   强调的「FACT/ESTIMATE 标注」思路
3. **Marketplace Bargaining 那个 demo 特别对口** —— 变量模板 + 优化后产出「可成交回复」，
   对 BOSS 的跨境电商议价场景有直接参考价值
4. **有 MCP Server 部署指南**（`docs/user/mcp-server_en.md`）—— 可挂进 MCP 生态

## 📁 相关文件

```
/opt/data/cache/scratch/dy5/
├── f_01..f_06.jpg        关键帧（5秒间隔，30秒视频）
├── ocr.py                帧 OCR 脚本
├── po_readme.md          README 全文（26,671 字节，via GitHub API）
└── t.json                转写 JSON
```

**踩坑**：README 抓取要用 GitHub API（默认分支是 `develop` 不是 `main`，
raw.githubusercontent.com/main 返回 14 字节空内容）。

## 🔗 相关

- 在线版：https://prompt.always200.com
- 文档：https://docs.always200.com
- DeepWiki：https://deepwiki.com/linshenkx/prompt-optimizer
- 本机同名但不同的技能：`/opt/nas/volume2/2-AI/skills/prompt-optimizer/`