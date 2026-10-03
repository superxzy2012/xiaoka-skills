---
title: "V26-HermesEngine百条命令手册"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/HZcXXSq5mhg/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "Hermes", "命令手册", "Gateway", "飞书", "主子Agent", "模型切换", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/HZcXXSq5mhg/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（整理 100 条 Hermes Engine 命令，点出 Gateway 接飞书/钉钉、模型切换、主子 Agent 架构）
> **可复用部分**：一条命令复刻 OpenClaw 记忆与 API Key；Gateway 配置接飞书/钉钉；切换模型命令；主/子 Agent 上下文隔离机制
> **对你项目的价值**：Hermes 的命令与架构参考——Gateway 接飞书印证你飞书路线的可行性，主子 Agent 架构对 agent 蜂群有启发

## 核心命令与机制

- **一条命令复刻 OpenClaw 的全部记忆与设置**（含 API Key 等），把 Hermes 体验提升一个档次
- **Hermes Gateway**：用来配置接入**飞书 / 钉钉**等
- **切换模型命令**：Hermes 有**主模型 + 辅助模型**两个；辅助模型可用 OpenRouter 里的免费模型
- **单条快速提问命令**：独立于主对话的快速问法
- **主 / 子 Agent 架构**：主 Agent 觉得某问题该发给不同子 Agent 时，**上下文会被隔离**——不是每个子 Agent 都能收到你这个问题

## 与你项目的关系

- **飞书连接印证**：视频明确说 Hermes Gateway 可接飞书/钉钉，与你已连飞书、从飞书指挥 WorkBuddy 的路线一致，说明「客户端 + 飞书网关」是企业化用法的成熟形态。
- **主/子 Agent 架构**：这正好对应你 OPC 一人公司想做的 **agent 蜂群**——不同子 Agent 处理 Ozon / 美客多 / 亚马逊不同平台的任务，上下文隔离避免互相干扰，是个值得复用的架构范式。
- 100 条命令手册作者已整理成文档，需要时可在其评论区索取；WorkBuddy 侧命令体系不同，但 Gateway / 模型切换 / 多 Agent 的思路可直接借鉴。
