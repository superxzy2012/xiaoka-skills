---
title: "V17-零Token用Codex详细配置手册"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/defzWIo7v9Y/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~100s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "Codex", "Codex++", "ChatCompletions", "配置手册", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/defzWIo7v9Y/`
> **转录引擎**：whisper-small｜**视频时长**：约 100 秒
> **质量评分**：⭐⭐⭐⭐⭐（最详尽的一篇——把「零 Token 接 Codex」的点位配置逐字段讲清，可作为配置手册）
> **可复用部分**：Token 自由系统 + Codex++ 的完整字段配置（接入方式 / Base URL / Key / 上游协议 / 模型获取 / 模型切换）
> **对你项目的价值**：WorkBuddy 的自定义 API 配置与 Codex 同构，这篇的字段可直接对照映射到 WorkBuddy

## 配置全流程（已纠正音译）

1. 打开 **Token 自由系统**（即「网页大模型转 API」工具），添加**供应商**，把要用的模型在**网页端**做认证后添加进来
2. 工具调用处选**普通 OpenAI 的 Tools**，托管选「自动」
3. 到 **API Key** 页复制 Key 备用
4. 需要 **Codex++** 工具（网页版 DeepSeek 已预装，这里演示接一个新模型）
5. 点「供应商配置」，关键字段：
   - **接入方式**：选「纯 API」
   - **配置模型**：先不填
   - **启用目标功能**：勾选
   - **Base URL**：填本地 `8080` 端口（即本地网关服务提供地址）
   - **Key**：粘贴刚才复制的 API Key
   - **上游协议**：只能选 **Chat Completions**
6. 点「从上游获取」→ 从「网页大模型转 API」工具处拿到**完整模型列表**，复制其中一个填进配置模型
7. 供应商配置里多出「供应商3」，自带测试功能，返回 **200** 即连接成功
8. 双击进 Codex，模型列表里出现该模型（如 `dbcqb4po`）

## 实测（工具调用 + 跨技能备份）

- 任务1：指定文件夹列出文件 → 准确返回
- 任务2：把 Hermes 里创建的某个 Skill 导包到另一个 Skill → Codex 因 Hermes 自身是独立环境、需申请写权限，点「允许」后备份成功
- **模型切换**：把当前模型切到 GLM，重启 Codex 桌面面板 → 重新获取模型列表时，**所有「网页大模型转 API」的模型都自动获取到了**，可在对话中任意切换零成本模型

## 与你项目的关系

- 这是「0 token 方法」最完整的**配置手册**。Codex 的自定义 API 字段（Base URL / Key / 上游协议 Chat Completions / 从上游获取模型）与 WorkBuddy 的自定义 API 入口**同构**。
- 直接可迁移到 WorkBuddy：把「网页大模型转 API」工具暴露的本地端点 + 模型名，按同样字段填进 WorkBuddy 自定义 API 即可零成本调用。
- 模型可热切换是亮点：同一套转 API 服务接入后，GLM / DeepSeek / Kimi 等免费模型随时切换，不另耗 Token。
