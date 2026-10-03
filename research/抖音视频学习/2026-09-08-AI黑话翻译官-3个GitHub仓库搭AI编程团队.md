---
title: "3 个 GitHub 仓库，搭建一整支 AI 编程团队"
source: "douyin"
url: "https://v.douyin.com/UC3A9GbFvSg/"
author: "AI黑话翻译官"
video_id: "76831【手机号】526"
duration: "28s"
publish_date: "2026-09-08"
tags: [AI编程, 多Agent, GitHub, 工具链, 效率]
confidence: A
ingested_at: 2026-09-08
repos_mentioned:
  - All-Hands-AI/OpenHands
  - PrimeIntellect-ai/prime-agent
  - ogulcancelik/herdr
---

# 3 个 GitHub 仓库，搭建一整支 AI 编程团队

> 来源：抖音 @AI黑话翻译官  |  28s 短科普  |  置信度 A

## 摘要
一句话总结：**用 3 个 GitHub 仓库把 Claude Code / Codex / OpenCode 等多 Agent 装进一个"统一工作台"，长任务后台跑 + 实时看每个 Agent 状态。**

## 核心观点（口播转写）

| 序号 | 仓库（whisper 听写） | 真实仓库 | 一句话功能 |
|---|---|---|---|
| 1 | **All-Card** | [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | 把 Codex / Claude Code 等多 Agent 放进一个界面并行处理不同任务 |
| 2 | **Prime Agent** | [PrimeIntellect-ai/prime-agent](https://github.com/PrimeIntellect-ai/prime-agent) | 支持长时间运行；子 Agent 任务交代后自动在后台推进 |
| 3 | **Herder** | [ogulcancelik/herdr](https://github.com/ogulcancelik/herdr) | 实时显示每个 Agent 状态（工作/空闲/卡住/完成），一眼看清 |

**使用方式**：把任务拆开 → 多 AI 同时写代码 → 改 bug / 跑流程 / 效率拉满

## 详细分析

### 1. All-Hands-AI / OpenHands
- **是什么**：OpenHands（原 OpenDevin）是 All-Hands-AI 团队开发的 AI 编程 Agent 平台
- **核心能力**：
  - 多 Agent 在一个统一 Canvas 里并行
  - 兼容 Claude Code、Codex、OpenCode 等
  - 可自托管 always-on 的"工程团队"
  - 把 Slack 报告、GitHub issue 拆解等任务自动化
- **链接**：<https://github.com/All-Hands-AI/OpenHands>
- **Top lang**: Python / HTML
- **BOSS 关联**：13BIT 已经在用的小米 codex（飞书）就是 Agent 的一种实例，OpenHands 提供的是多 Agent 编排 + UI 编排

### 2. PrimeIntellect-ai / prime-agent
- **是什么**：开源的 coding & research agent，专注"长时间运行 + 后台任务"
- **核心能力**：
  - **Daemon-backed sessions** - terminal 断开后 agent 还在跑，可 reattach
  - **自动压缩** - 长时间任务的 context 不会爆
  - **持久目标（persistent goals）** - 跨 turn/会话保持目标
  - **心跳 + 调度** - 定期触发任务
  - **保留子 agent** - 跨 turn 保留
  - **Autonomous mode** - 自动避免重复跑同一失败 gate
- **关键命令**：
  ```bash
  prime-agent list
  prime-agent attach <agent>
  prime-agent schedule add worker "0 9 * * 1-5" -- "Review open work"
  ```
- **性能数据**（来自 arXiv 论文）：在 ARC-AGI-3 RHAE Best@1 从 30% 提升到 95.5%
- **链接**：<https://github.com/PrimeIntellect-ai/prime-agent>
- **BOSS 关联**：13BIT 的多 agent 系统（如阿正·网安/小米 codex）目前是手动启动，prime-agent 提供"永不丢失任务"的语义层

### 3. ogulcancelik / herdr
- **是什么**：终端级的 AI Agent 多路复用器（terminal multiplexer + agent state detection）
- **核心能力**：
  - **tmux-like 多 session** + agent state awareness
  - **4 状态机**：blocked（等你输入） / working（输出中） / done（完成） / idle（空闲）
  - **侧栏常显** - 不需要 scroll panes 找哪个 agent 卡住了
  - **持久会话** - 关闭 terminal agents 还在
  - **SSH 远程** - 服务器跑 agents 笔记本/手机监控
  - **Unix socket API** - bash 脚本可以内省 agent 状态
- **集成 14 个 Agent**：pi, omp, claude, codex, copilot, devin, droid, kimi, opencode, kilo, hermes, qodercli, cursor, mastracode
- **Stars**: ~30k（2026-08 爆炸式增长）
- **链接**：<https://github.com/ogulcancelik/herdr>
- **作者**：Oğulcan Çelik（土耳其开发者）
- **版本**：v0.8.0 (2026-08-15)，单 Rust binary
- **BOSS 关联**：13BIT GM/agent bot 集群目前没有"侧栏 dashboard"，herdr 提供了终端版的状态可视化

## 三个工具组合的"完整 AI 编程团队"

```
┌─────────────────────────────────────────────────────────┐
│ OpenHands Canvas (UI 编排层)                              │
│   ├─ Claude Code  ├─ Codex  ├─ OpenCode  ├─ 其它        │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ prime-agent (长任务调度层)                                  │
│   ├─ daemon session  ├─ schedule  ├─ persistent goals   │
└────────────┬────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────┐
│ herdr (状态可视化层)                                       │
│   ├─ blocked  ├─ working  ├─ done  ├─ idle              │
└─────────────────────────────────────────────────────────┘
```

## BOSS 价值评估

✅ **强推荐**：
- 3 个仓库都是 **Apache/AGPL/开源**，可商用
- 3 个都跟 13BIT 现有 Agent 集群形态高度契合
- herdr 单 Rust binary 安装简单，可以立即试
- prime-agent 解决了"长任务丢失"的痛点
- OpenHands 已经是被广泛使用的项目

⚠️ **风险**：
- 这 3 个组合起来**没有官方整合方案** - 需要自己接
- herdr v0.8 还在快速迭代（29k stars 但 issue 160+ 开）
- prime-agent 主要面向研究评估场景

## 行动建议

### 第一步（立即）
- [ ] 装 herdr 单 binary 试一下（最简单）
- [ ] 跑 `prime-agent list` 看现有 agent 能不能 attach

### 第二步（评估）
- [ ] 看 OpenHands 能否替代 13BIT 现有 OpenClaw 网关
- [ ] 评估 13BIT GM 群是否需要 herdr 状态侧栏

### 第三步（决策）
- [ ] 30 天内：herdr 进 13BIT GM 工具栈（terminal dashboard）
- [ ] 60 天内：prime-agent 接 13BIT 现有 agent 集群
- [ ] 90 天内：评估 OpenHands Canvas 是否替代 OpenClaw

---

## 原始转写（whisper）

> 3 个 GitHub 仓库搭建一整支 AI 编程团队
> 第一个 All-Card 把 Codex Cloud Code 等多个 Agent
> 放在一个界面里同时处理不同任务
> 第二个 Prime Agent 支持长时间运行
> 还能调用自 Agent 任务交代后自动在后台推进
> 第三个 Herder 实时显示每个 Agent 的状态
> 谁在工作 谁空闲 谁卡住 一眼就能看清
> 把任务拆开 让多个 AI 同时写代码
> 改 Bug 跑流程 效率直接拉满
> 关注我 学会更多 AI 实用小技巧

---

## 链接

- 抖音原视频：<https://v.douyin.com/UC3A9GbFvSg/>
- OpenHands：<https://github.com/All-Hands-AI/OpenHands>
- prime-agent：<https://github.com/PrimeIntellect-ai/prime-agent>
- herdr：<https://github.com/ogulcancelik/herdr>

MEDIA:/Users/【BOSS英文名】/WorkBuddy/douyin-tmp/UC3A9GbFvSg/76831【手机号】526.mp3