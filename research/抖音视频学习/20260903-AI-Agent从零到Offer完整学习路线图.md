---
title: "AI Agent 从零到 Offer：完整学习路线图（6 阶段 · 6-9 个月）"
source: "https://v.douyin.com/OtnpYTWVXCE/"
platform: douyin
type: image_post
author: "AI大模型知识分享"
content_source: "问问知识库"
published: 2026-09-03
captured: 2026-09-03
tags: [douyin, ai-agent, 学习路线, langchain, rag, multi-agent, prompt工程]
confidence: A
---

## 来源

- 抖音链接：https://v.douyin.com/OtnpYTWVXCE/
- 作者：AI大模型知识分享
- 内容来源：问问知识库（Jack/Aron/Blake 等作者）
- 形式：图文帖（16 张图）
- 抓取时间：2026-09-03

---

## 📋 总览：6 阶段学习路线

| 阶段 | 主题 | 周期 | 核心目标 |
|------|------|------|---------|
| 阶段 1 | 大模型基础 | 35~45 天 | 理解 Transformer/Token/推理参数，能调 API |
| 阶段 2 | Prompt 工程 | 25~35 天 | 系统掌握提示词设计与优化方法 |
| 阶段 3 | RAG 增强检索 | 30~40 天 | 向量库+检索+重排，搭建完整 RAG 系统 |
| 阶段 4 | Agent 核心 | 40~45 天 | ReAct/Plan-and-Execute/Tool Use/MCP/记忆 |
| 阶段 5 | 多智能体与工程化 | 35~45 天 | Multi-Agent/部署/监控/评估 |
| 阶段 6 | 项目实战与进阶 | 45~60 天 | 完整项目+面试准备 |

> 每天 2~4 小时，全周期约 **6~9 个月**

---

## 📖 阶段详解

### 阶段 1：大模型基础（35~45 天）

**学习目标：**
- 理解 Transformer 为何成为现代大模型的骨架
- 掌握 Token、Tokenizer 基本概念
- 了解 temperature/top-p/max_tokens 等推理参数影响
- 能用 Python 调用至少一种大模型 API

**核心模块：**
- 数学直觉（向量、点积、相似度）
- Transformer（Encoder-Decoder 与 Decoder-only 的区别 / Self-Attention / 多头注意力）
- 位置与上下文（位置编码 / 上下文长度限制）
- Tokenization（BPE/WordPiece / 特殊 token / 中英文差异）
- 推理参数（temperature / top-p/top-k / penalty / stop sequences）
- 实践：写最小脚本 → 多轮对话 / 流式输出 / 参数对比实验

**关键资源：**
- 📄 [Attention Is All You Need](https://arxiv.org/abs/1706.03762)（经典论文）
- 🖼️ [The Illustrated Transformer](https://jalammar.github.io/illustrated-transformer/)（强烈推荐图解）

**阶段末自测：** 不看资料能画出「请求 → Tokenize → 模型 → 解码 → 文本」流程；能解释提高 temperature 后回答为何更发散。

---

### 阶段 2：Prompt 工程（25~35 天）

> 图文中未单独展开，路线图第一天即涉及 Prompt Engineering 进阶

---

### 阶段 3：RAG 增强检索（30~40 天）

**路线图提及：**
- RAG 增强检索（LlamaIndex 中文指南）
- 向量数据库实战（Pinecone / Chroma 教程）

---

### 阶段 4：Agent 核心（40~45 天）⭐ 重点

**学习目标：**
- 理解 Agent 循环：观察 → 思考 → 行动 → 更新状态
- 掌握 ReAct 与 Plan-and-Execute 的差异与适用场景
- 熟练使用 Function Calling / Tool Use
- 了解 MCP（Model Context Protocol）基本思想
- 掌握记忆分层：短期 / 长期 / 用户画像

**核心模块：**

| 模块 | 具体任务 |
|------|---------|
| **ReAct** | 读论文还原流程；用 LangChain/LlamaIndex Agent 或自写最小循环实现「查天气+计算」类 demo |
| **Plan-and-Execute** | 多步任务拆解；失败重试；子任务委托 |
| **Function Calling** | OpenAI/Anthropic tool 定义；解析 tool_calls；错误处理与超时 |
| **MCP** | 阅读规范；跑通官方/社区 server 示例；理解「谁连接谁」 |
| **记忆** | 对话截断与摘要；用向量库存「用户事实」；隐私与权限 |

**关键资源：**
- 📄 [ReAct 论文](https://arxiv.org/abs/2210.03629)
- 🧩 [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)（复杂 Agent 流与状态）
- 🔌 [MCP 官方文档](https://modelcontextprotocol.io/) / [GitHub](https://github.com/modelcontextprotocol)
- 🎓 DeepLearning.AI 相关短课

**阶段末自测：** 实现一个「带 2~3 个工具」的 Agent，能处理多步问题并有基本重试；能口述 MCP 与「普通 function calling」在架构上的区别。

---

### 阶段 5：多智能体与工程化（35~45 天）

**路线图提及：**
- 多 Agent 协作系统（Multi-Agent Systems 论文）
- Agent 评估与测试（AgentBench）
- 部署与监控（LangSmith / LangServe）
- 企业级 Agent 案例

---

### 阶段 6：项目实战与进阶（45~60 天）

**路线图提及：**
- Agent 项目实战（构建个人助理 Agent）
- 复杂任务规划（BabyAGI 原理）
- AI Agent 专家进阶（LLM 微调与优化）
- 前沿研究追踪（arXiv AI Agent 论文）

---

## 🧩 Agent 九种设计模式（图文亮点）

来源：Jack《万字详解：AI Agent 系统架构设计》

**1. ReAct 模式**
- 2022 年 10 月发表，LLM Agent 第一篇
- 核心：推理（Reasoning）与行动（Action）交错进行
- 类比：找胡椒粉时，找到就停（有 ReAct）vs 所有地方都搜一遍（无 ReAct）

> 图文仅展示了第 1 种，其余 8 种待补充

---

## 🏗️ Agent 三层架构

来源：Jack《万字详解：AI Agent 系统架构设计》

| 层级 | 作用 | 包含 |
|------|------|------|
| **工具层（Tool/Retrieval）** | 系统的基础，与外部数据/服务交互 | API、向量数据库、知识库、SaaS 平台 |
| **行动层（Action/Orchestration）** | 协调 LLM 与外部世界的交互 | 执行 LLM 的行动指令 → 返回结果给推理层 |
| **推理层（Reasoning）** | 系统智能的核心 | 用 LLM 处理信息 → 决定下一步做什么 |

> 推理不充分 → 重复查询 / 不一致；工具质量差 → 检索不到相关数据

---

## 🧠 MemAgent：构建 LLM "无限记忆"

来源：Aron《宇宙厂 MemAgent，构建 LLM "无限记忆"！》

**核心思想：** 不是试图无限拓宽上下文窗口（加宽"书桌"），而是**模仿人类做笔记**——把信息提炼后存入记忆，需要时再调取。

**认知工作流：**
1. **初始化** — 记忆缓冲区从空白开始
2. **迭代精炼（Iterative Refinement）** — 逐块处理文档流，不断更新记忆
3. **最终合成（Final Generation）** — 基于精炼后的记忆回答问题

**优点：**
- 线性成本（Linear Cost）：记忆成本不随文档长度指数增长
- 模仿人类认知：边读边做笔记，而不是一次塞下所有内容

---

## 💼 实战项目案例

### 1. 基于多 Agent 的电商推荐系统
- **作者：** Blake
- **核心：** 推荐 Agent + 文案 Agent + 库存 Agent 协同工作，Supervisor 统一编排
- **解决痛点：** 推荐与库存脱节 / 文案千篇一律 / 各系统各自为战
- **技术栈：** Multi-Agent / Supervisor 模式 / LangGraph / asyncio 并行 / Redis / Feature Store / A/B Testing / Thompson Sampling / RAG / ReAct / MiniMax LLM

### 2. FinRobot：金融分析 Agent
- **四层架构：** 金融 AI Agent 层 → 金融 LLM 算法层 → LLMOps & DataOps 层 → 多源 LLM 基础模型层
- **核心机制：** Smart Scheduler — 无缝集成多源 LLM，为特定金融任务选最合适的模型

### 3. 数据分析智能体
- **四层架构：** 数据接入 → 智能分析 → 模型管理 → 输出呈现
- **代码框架：** AnalysisTask dataclass + DataAnalysisAgent 核心类

### 4. Cursor + Agent 生成高保真 UI 原型图
- 自然语言描述 → 几秒出可视化设计参考
- 结构化 Prompt 模板驱动

---

## 🔧 工具与平台速查

| 工具/平台 | 用途 |
|-----------|------|
| **LangChain / LangGraph** | Agent 框架 / 复杂流与状态管理 |
| **LlamaIndex** | RAG 框架 |
| **MCP** | 标准化工具与上下文供给协议 |
| **Coze / 扣子** | 低代码 Agent 开发平台（字节出品） |
| **Dify** | 开源 LLM 应用开发平台 |
| **Cursor** | AI 编程 IDE（带 Agent 模式） |
| **Pinecone / Chroma** | 向量数据库 |
| **LangSmith** | Agent 调试与监控 |
| **LangServe** | LangChain 应用部署 |
| **AgentBench** | Agent 评估基准 |

---

## 📌 对 13BIT 团队的启示

1. **Agent 三层架构** 与我们当前 OpenClaw 的架构基本吻合（工具层=MCP/插件，行动层=gateway 编排，推理层=模型）
2. **MemAgent 记忆思路** 与我们的多层记忆体系不谋而合——值得参考其「迭代精炼」算法优化记忆效率
3. **多 Agent 电商推荐系统** 是直接可参考的落地案例——推荐/文案/库存三 Agent 协同 = 我们 13BIT 团队的镜像
4. **MCP 是必学协议** — 标准化工具接入，避免每个平台各搞一套

---

## 原始图文（关键帧）

![总图](attachments/20260903-OtnpYTWVXCE/image-001.jpg)
![阶段1基础](attachments/20260903-OtnpYTWVXCE/image-002.jpg)
![阶段4Agent核心](attachments/20260903-OtnpYTWVXCE/image-003.jpg)
![Agent入门](attachments/20260903-OtnpYTWVXCE/image-004.jpg)
![Agent架构设计](attachments/20260903-OtnpYTWVXCE/image-014.jpg)
![MemAgent记忆](attachments/20260903-OtnpYTWVXCE/image-016.jpg)

> 完整 16 张原图 + OCR 全文见附件目录：`attachments/20260903-OtnpYTWVXCE/`

---

## 附：完整 OCR 文本（可折叠）

<details>
<summary>点击展开 16 张图完整 OCR（约 1.8 万字）</summary>

```text
[完整 OCR 见 attachments/20260903-OtnpYTWVXCE/ocr_all.txt]
```

</details>
