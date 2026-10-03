---
title: "AI上下文省98%！长任务不再失忆 mksglu/context-mode"
source: "https://v.douyin.com/JMPlJm9e-Yk/"
platform: douyin
type: video
author: "翻奇兽AI"
published: 2026-08-25
captured: 2026-09-18
video_id: "768641【手机号】76"
tags: [douyin, AI编程, MCP, 上下文管理, context-mode, 开源工具, Claude-Code, Cursor]
summary: "context-mode 是一个 2.3 万星的 MCP 工具，把 AI 编程中 MCP/工具的海量输出挡在上下文门外做沙箱压缩（315KB→5.4KB，省 98%），并把改动/报错/任务存进本地数据库，长任务压缩对话后不丢进度，支持 17 个 AI 编程客户端。"
confidence: A
---

# AI上下文省98%！长任务不再失忆 mksglu/context-mode

> [!abstract] 摘要
> 介绍 GitHub 开源项目 **mksglu/context-mode**（TypeScript，约 23,130 Stars，单周新增超 1900 星）：一个专攻 **AI 编程上下文爆仓**问题的 MCP 工具。它把工具输出先送进沙箱压缩（实测 315KB → 5.4KB，**省 98% 上下文**），并将每次改动、报错、任务持久化到本地数据库，对话压缩后还能接着干、不丢进度；通过 MCP + hooks 接入 17 个编程平台，装完自动生效。

## 核心要点

| # | 要点 | 说明 |
|---|------|------|
| 1 | **解决痛点** | AI 干到一半上下文就满、聊着聊着忘了改到哪；长任务反复交代上下文 |
| 2 | **核心机制** | 不用手动精简对话/删记录，自动把海量工具输出挡在上下文门外，先进沙箱压缩 |
| 3 | **压缩效果** | 实测工具输出 **315KB → 5.4KB，省 98%** 上下文 |
| 4 | **记忆持久化** | 每次改动、报错、任务都存进**本地数据库**；对话压缩后还能接着干，不丢进度 |
| 5 | **接入方式** | 通过 MCP + hooks；支持 **17 个平台**：Claude Code、Gemini、Cursor、Antigravity 等 |
| 6 | **安装体验** | 装完自动生效 |
| 7 | **项目数据** | GitHub `mksglu/context-mode`，TypeScript，约 2.3 万总星，单周新增 1900+ 星；62 Issues / 41 PRs（截帧时） |

## 关键信息卡

- **仓库**：`github.com/mksglu/context-mode`
- **语言/类型**：TypeScript · MCP 工具（Public）
- **官方一句话**：Context window optimization for AI coding agents. Sandboxes tool output (98% reduction), persists session memory, and enforces routing across 17 platforms via MCP + hooks.
- **三大能力**：① 沙箱化工具输出（省 token）② 会话记忆持久化（本地 DB）③ 跨 17 平台的路由/管控
- **适用人群**：用 Claude Code / Cursor / Gemini CLI 等做长任务、经常被上下文长度拖垮的开发者
- **获取方式**：视频引导评论区扣 "Code / 省上下文" 自取开源地址（实际仓库即上方 GitHub 链接）

## 关键画面

![[f_03.png]]
GitHub 项目主页：mksglu/context-mode，2.3 万总星，TypeScript，MCP 工具，简介明确写 98% reduction + 17 platforms。

![[f_01.png]]
封面：AI 上下文省 98%，长任务不再失忆。

![[f_05.png]]
工具输出沙箱压缩演示：315KB → 5.4KB。

（其余帧 f_02/f_04/f_06–f_10 为口播配画面与平台 logo 轮播，已一并存档。）

## 口播 / 转录全文

> AI 干到一半，上下文就满了；聊着聊着忘了改到哪。
>
> 拿下 2.3 万总星的 Context Mode，TypeScript 开发，单周新增超 1900 星，是专门解决 AI 编程上下文爆仓问题的 MCP 工具。
>
> 不用你精简对话、删旧记录，它自动把海量工具输出挡在上下文门外——工具输出先进沙箱压缩，315KB 直接变 5.4KB，省掉 98% 的上下文。
>
> 每次改动、报错、任务都记进本地数据库，对话压缩后还能接着干，不丢进度。
>
> Claude Code、Gemini、Cursor 等 17 个平台都能装，装完自动生效。
>
> 长任务做到一半总失忆的，再也不用重复交代上下文了。开源地址整理好了，评论区 Code「省上下文」自取。

## 与本机/13BIT 工作流的关联（小豆备注）

- 本集群大量使用 Claude Code / Codex / Cursor 类 agent 跑长编码任务，**上下文爆仓是真实高频痛点**，context-mode 的"工具输出沙箱化 + 本地会话记忆"与 Hermes 的记忆/压缩副驾模型思路一致，值得实测对比。
- 建议动作：待 BOSS 确认后，可 `git clone` 该仓库 → 走 research-and-arm 流程（安装 → 封装为 Hermes 技能）。
- ✅ **仓库已核验（2026-09-18 GitHub API）**：`mksglu/context-mode` 真实存在，**23,393 Stars**（与视频 2.3 万一致），TypeScript，创建于 2026-02-23，**最近 push 2026-09-17（活跃维护中）**，未归档。数据可信。

## 小豆本机实测（2026-09-18，真跑非纸面）

下载 v1.0.169 源码（`~/WorkBuddy/context-mode-test/`），用独立 MCP 客户端经 stdio 直连其 server，真实调用通过：

- **MCP 握手 + 11 个工具**：`ctx_execute / ctx_execute_file / ctx_index / ctx_search / ctx_fetch_and_index / ctx_batch_execute / ctx_stats / ctx_doctor / ctx_upgrade / ctx_purge / ctx_insight`，沙箱支持 javascript/shell/typescript/python。
- **① 沙箱压缩实测**：脚本在沙箱内生成 **8000 行 / 1009.2 KB** JSON，做分组+求和，只把 5 行结论 `console.log` 出来 → **实际返回 831 字节**（比官方宣称的 98% 还彻底）。大数据零进上下文，机制属实。
- **② 跨会话记忆实测**：进程 A 用 `ctx_index` 写入一条"决策/进度"→ 关闭进程 → 全新进程 B（模拟对话压缩/重开）用 `ctx_search` 检索，**成功取回原文**（SQLite + FTS5/BM25 持久化在本地）。"长任务不失忆"机制属实。
- **License 注意**：**ELv2（Elastic License 2.0）**，非严格 OSI 开源——禁拿去做托管服务、禁绕过限制；自用/内部用没问题，商业化集成前需看 LICENSE。

### 能不能直接接进小豆（Hermes）？
- 它是标准 stdio MCP server，Hermes 可经 MCP 配置挂载，但**不能在当前会话热插拔**，需改 config 并重载，属主链路改动（要 BOSS 点头）。
- 官方主战场是 **Claude Code / Cursor / Gemini CLI / Codex 等 17 个编程客户端**（MCP + hooks 注入路由规则，还自带 openclaw 适配器）。
- **小豆建议**：小豆日常是运维/入库/调研，收益有限；最该装的是 **Claude Code 长编码任务**（BOSS 已在用）。要不要我先在 Claude Code 上试点？

## 来源

- 抖音链接：https://v.douyin.com/JMPlJm9e-Yk/
- 作者：翻奇兽AI
- 发布：2026-08-25
- 抓取时间：2026-09-18
- video_id：768641【手机号】76
