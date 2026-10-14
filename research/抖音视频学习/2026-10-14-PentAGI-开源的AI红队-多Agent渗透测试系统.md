---
title: PentAGI — 开源的「AI 红队」多 Agent 自主渗透测试系统
date: 2026-10-14
source: 抖音
source_url: https://v.douyin.com/qOJ9RKeNNWs/
author: 大豪老师（AI版）
series: OPEN SOURCE · 第 02 集（上一集：REA）
tags: [AI, 安全, 渗透测试, 多Agent, PentAGI, 开源项目, 红队, 知识图谱, 合规风险]
confidence: high
---

# PentAGI — 开源的「AI 红队」

> 来源：抖音「大豪老师（AI版）」· 2026-10-14 采集（视频 38 秒）
> 原文链接：https://v.douyin.com/qOJ9RKeNNWs/ （视频 ID: 7696129649662993083）
> 置信度说明：**high** —— 视频画面直接拍到 GitHub 仓库页与官网，且已通过 GitHub 原仓库 / 官网 / 第三方技术媒体三方交叉核实。
> 系列说明：本条是「大豪老师」开源系列**第 02 集**，第 01 集就是上一份笔记的 **REA**（视频开头明说"REA 的热度还没过去"）。

## 视频转写（whisper small · zh）

<details>
<summary>点击展开完整口播（38 秒）</summary>

```
卧槽，REA 的热度还没过去，PentAGI 又冲上了一个更狠的项目，
有人把一支 AI 红队开源了，它叫 PentAGI。

你给它一个经过授权的测试目标，多个 AI agent 就会分工制定计划，
在隔离环境里调用 20 多种专业工具，边测试边记录，
发现最后整理成漏洞报告。

它还能记住之前查到的线索，让后续分析接着往下走。

以前做渗透测试，很多人不就要反复切工具整理结果。
现在有人把这套协作流程交给 AI 自主推进，
网络安全行业的工作方式真要开始变了。

关注我，每天分享一个 AI 玩法。
```

> ⚠️ 转写校正：whisper 把 **PentAGI** 听成 "Pentageye"；"边测试边记录" 原听作"编测试编记录"。
> 项目名由**关键帧 OCR 直接读屏确认**，非听写推断。

</details>

## 关键帧 OCR（vision_ocr · 画面为官网 + GitHub 仓库页）

| 帧 | 画面文字（节选） | 信息点 |
|---|---|---|
| f_01 | `LAST EPISODE / REA`、`2,503 Commits` | 开篇回顾上一集 REA |
| f_03 | `PentAGI: Advanced AI-Powered Penetration Testing`、**`GITHUB TRENDING #1 Repository Of The Day`**、`A Multi AI Agent that performs complicated penetration testing tasks using terminal, browser, editor, and external search system.` | 项目定位 + **当日 GitHub Trending 第一** |
| f_05 | `How It Works` ① `Define Task` → `AI Analysis`；`GITHUB README / TEAM OF SPECIALISTS`：*Delegation system with specialized AI agents for research, development, and infrastructure tasks* | 工作流 + 专家 Agent 分工 |
| f_08 | `PENTAGI.COM / PERSISTENT MEMORY`：**History Tracking**（`All commands and outputs are saved in PostgreSQL`）+ **Knowledge Graph RAG**（`Semantic memory powered by Graphiti and Neo4j`）；README：*Smart Memory System — Long-term storage of research results and successful approaches* | 持久记忆双层设计 |
| f_11 | `Dashboard / Analytics`、`Flows Activity Over Time`（Flows, tasks, and subtasks created per day） | 可视化监控面板 |
| f_13 | `GITHUB / VXCONTROL / PENTAGI`、`952 Commits` | 确认真身：**vxcontrol/pentagi** |

## 核心信息（2026-10-14 联网核实）

| 项 | 值 |
|---|---|
| **项目名** | **PentAGI** = **Pen**etration testing **A**rtificial **G**eneral **I**ntelligence |
| **一句话定位** | 全自主多 Agent 系统，自动完成复杂渗透测试任务 |
| **GitHub** | `github.com/vxcontrol/pentagi` — **28.2k stars** |
| **官方站** | pentagi.com |
| **License** | MIT |
| **主语言** | Go 61.3% + TypeScript 35.7% |
| **活跃度** | 952 commits，最新提交 2026-10-09（采集时 4 天前），10 tags |
| **贡献者** | 20+ 人，**含 `@claude` 等 AI Agent 账号**（与 REA 同一现象） |

### 它到底干什么

给它一个**经过授权**的测试目标，多个 AI Agent 分工协作，全程自主推进：

| 步 | 动作 |
|---|---|
| 1 | **Define Task** — 你指定渗透测试任务 |
| 2 | **AI Analysis** — 分析任务并确定最佳路径 |
| 3 | **Team of Specialists** — 专家 Agent 分工（研究 / 开发 / 基础设施），可开执行监控与任务规划 |
| 4 | **隔离执行** — 全部操作在**沙箱化 Docker 环境**内完成，完整隔离 |
| 5 | **专业工具** — 调用 20+ 渗透测试专业工具（terminal / browser / editor / 外部搜索） |
| 6 | **详细报告** — 生成含利用指南的漏洞报告 |

### 三个真正值得看的工程设计

1. **持久记忆双层**（视频重点讲的"它能记住之前查到的线索"）
   - **History Tracking**：所有命令与输出存 PostgreSQL —— 可回溯"我做过什么"
   - **Knowledge Graph RAG**：Graphiti + Neo4j 语义记忆 —— 理解"这些线索之间什么关系"
   - 这是"让后续分析接着往下走"的技术底座，不是简单的对话历史

2. **Advanced Agent Supervision**（对**小模型**是关键）
   - **Recovery Mechanism**：按具体失败模式给上下文指导
   - **Limit Enforcement**：工具调用触顶时协调优雅终止
   - 官方实测：**<32B 参数模型必须开启** Execution Monitoring + Task Planning（以 Qwen3.5-27B-FP8 验证）

3. **可观测性**：内置 Grafana / Prometheus 系统监控 + Langfuse LLM 观测面板

### 模型与部署

- 支持 OpenAI / Anthropic / **Google Gemini** / Azure OpenAI / 自定义 endpoint / 开源模型（vLLM、Ollama 等）
- Docker Compose 一键起：`docker-compose.yml`（+ 可选的 `-graphiti` / `-langfuse` / `-observability` 三套叠加）

## ⚠️ 一个必须记下的关键事实：开源版没有 MCP

原仓库 README 的 commit 说明里写得很明确：

> *"the open-source edition has no MCP code, and Enterprise adds MCP servers."*
> （开源版**不含 MCP 代码**，MCP server 是企业版才有的功能）

这一点很重要 —— 如果按"接 MCP"的思路去规划（像 REA 那样），**开源版接不了**，得走它的 API / GraphQL，或上企业版。

## 观点 / 待验证

1. **它和 REA 不是一类东西，别混为一谈。** REA 是**给 Agent 用的逆向工程 MCP 工具**（工具层）；PentAGI 是**一整套自主渗透测试系统**（平台层，自带 Go 后端 + React 前端 + PostgreSQL + Neo4j + Docker 沙箱）。REA 装完接进现有 Agent 就能用；PentAGI 是**独立部署一套栈**，是"再起一个系统"而不是"给现有 Agent 加个能力"。

2. **真正的创新不是"多 Agent"，是"记忆 + 可恢复"。** 多 Agent 分工早已不新鲜。PentAGI 的硬工程在于：命令输出落 PostgreSQL（可审计）、语义关系进 Neo4j 知识图谱（可推理）、失败模式有专门的 Recovery Mechanism（可恢复）。**"跑不完的渗透测试能接着跑"**才是它区别于玩具的地方 —— 这跟我们做长周期 Agent 任务时踩的"断点续跑"是同一类难题。

3. **对我们（13BIT）的定位：可以看，不建议直接上。**
   - ⚠️ **合规边界**：PentAGI 的定位是**授权渗透测试**。国内未授权渗透测试直接触犯《刑法》285/286 条。**绝不可**拿它扫任何非自有、未书面授权的目标（含竞品站、供应商系统）。
   - ✅ **合法且高价值的用法**：扫描**自有资产** —— 自家独立站、店铺后台、API 网关、云主机暴露面自查。这是最实际的价值点：把"安全巡检"从人工变自动化。
   - ⚠️ **成本不低**：完整栈要跑 Docker 多容器（Go 后端 + React 前端 + PostgreSQL/pgvector + Neo4j + 可选 Grafana/Langfuse/MinIO），**且会持续烧 LLM token**（多 Agent 长链推理）。不是轻量玩具。
   - ⚠️ **开源版无 MCP**，与我们 Hermes 集群的原生 MCP 能力对不上，集成路径要另想。

4. **值得借鉴到我们自己体系的一点**：它的 **Recovery Mechanism（按失败模式给上下文指导）**。我们多 Agent 体系里 Agent 失败后基本是"重试或放弃"，缺少"识别失败模式 → 针对性给上下文 → 接着干"这一层。这条可以往我们的长任务编排里搬。

5. **待验证（下次可做）**：
   - [ ] 本机是否满足部署前置（Docker 资源、Neo4j 内存占用）—— 16GB Mac 跑完整栈要评估
   - [ ] 官方 README 里 "20+ 专业工具" 的**具体清单**（视频口播说 20 多种，未逐条核实）
   - [ ] Enterprise 版 MCP server 的实际能力边界（是否值得为此付费）
   - [ ] 其 Recovery Mechanism 的实现细节能否借鉴进 `workflow/` 系技能

## 附件

- `attachments/20261014-7696129649662993083/f_01.png` ~ `f_13.png`（共 13 帧，fps=1/3）

## 来源

- 抖音原视频：https://v.douyin.com/qOJ9RKeNNWs/
- GitHub 原仓库：https://github.com/vxcontrol/pentagi （28.2k stars）
- 官网：https://pentagi.com
- 第三方技术媒体：LinuxToday《PentAGI: Open-source Autonomous AI Penetration Testing System》（2026-05-13）
- 关联笔记：`2026-10-13-REA-18万Star的AI逆向工程工具-开源项目.md`（同系列第 01 集）
