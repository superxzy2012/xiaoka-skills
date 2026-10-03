---
title: "V16-Codex加加让Codex接免API做选品VBcoding"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/LntGwyRcckU/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~90s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "Codex", "Codex++", "VibeCoding", "电商选品", "协议转换", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/LntGwyRcckU/`
> **转录引擎**：whisper-small｜**视频时长**：约 90 秒
> **质量评分**：⭐⭐⭐⭐⭐（给出 Codex 接免 API 的真实卡点与「Codex++」解法，并用电商选品项目实测）
> **可复用部分**：Codex++ 做请求协议转换 + 健康检查 + 用免 API 模型做 Vibe Coding 的完整链路
> **对你项目的价值**：免费网页模型不仅能聊天，还能在 Codex 里做真实 Vibe Coding（如更新你的跨境选品项目），且零 Token

## 原理与卡点

- 先通过**协议转换**，把 Web 端大模型转为 OpenAI 形式的 API
- 但 Codex 自身用了**非标准请求**，与标准 OpenAI 协议不兼容
- 解法：中间加一个 **Codex++** 工具，专门做请求格式转换

## 实操步骤

1. 启用「网页大模型转 API」工具，打开代理
2. 启动 **Codex++ 管理控制台**
3. 配置技巧：若之前配过类似模型，直接**点「复制」生成副本再编辑**，比重建方便——只需在模型列表里重选目标模型填上
4. 启动前先做**健康检查**，再启动 Codex++
5. 验证 Base URL 指向**本地网关服务** → 证明用的是免费 API

## 实测（电商选品 Vibe Coding）

- 任务：作者在代码平台（Gatehawk）上开源的一个**电商选品项目**（v1.0.2）做了更新，想用 Codex 把更新提交上去
- 结果：版本号确实更新、内部代码也更新成功
- 作者提醒：做 Vibe Coding 一定要先学会版本管理

## 与你项目的关系

- 这是「0 token 方法」在**编码 Agent（Codex）**上的落地：免费网页模型经 Codex++ 转换后，能在 Codex 里跑真实编码任务。
- 对 WorkBuddy：WorkBuddy 同样支持自定义 API，可把同一套「网页大模型转 API + 协议转换」接进来，用于你的 OPC 跨境选品项目自动化（脚本、数据抓取、页面生成等），全程零成本。
- 提醒：作者强调 Vibe Coding 务必配合版本管理（Git），避免免费模型改坏代码。
