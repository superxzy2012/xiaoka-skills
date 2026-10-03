---
source: "抖音 @李君陌"
url: "https://v.douyin.com/d1uZAGlDfkg/"
date: 2026-08-04
tags: [Hermes Agent, 高级技巧, 能力提升]
confidence_level: B
source_type: third_party
---

# 新手装完Hermes学会这5招，智能和能力提升2倍

## 核心内容（270字）

深入 Hermes Agent 的 5 个高级技巧，可以让智能体的能力成倍提升。视频从实操角度展示了：如何利用子代理（Sub-agent）机制并行处理复杂任务、如何配置 MCP 服务器扩展 Hermes 的工具生态、如何编写高效的系统提示词（System Prompt）来引导 Agent 行为、如何利用多轮对话上下文保持 Agent 的连贯性，以及如何结合外部 API 让 Hermes 具备实时数据获取能力。这些技巧能将 Hermes 从简单的聊天机器人升级为真正的智能工作助手。

## 关键操作步骤

1. **子代理**：使用 `delegate_task` 功能将任务拆分给多个子 Agent 并行处理
2. **MCP 扩展**：在 config.yaml 中添加 mcp_servers 配置，连接外部工具
3. **提示词工程**：编写高质量的 SKILL.md 系统提示词
4. **上下文管理**：使用 `--continue` 和 `--resume` 管理长对话
5. **外部集成**：通过 MCP 连接数据库、API 等外部数据源

## 适用场景
- 已掌握 Hermes 基础用法，想要进阶的用户
- 需要 Hermes 处理复杂多步任务的场景

## 注意事项
- 子代理会增加 Token 消耗
- MCP 服务器需要额外的安装和配置