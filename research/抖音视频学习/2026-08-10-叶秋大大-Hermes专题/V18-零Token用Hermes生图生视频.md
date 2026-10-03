---
title: "V18-零Token用Hermes生图生视频"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/0W1-rrPdGSY/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "Hermes", "生图", "生视频", "Skill", "Web大模型", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/0W1-rrPdGSY/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（证明零 Token 不止于文本，还能驱动生图生视频，且 Skill 通用）
> **可复用部分**：用「网页大模型转 API」+ 通用 Skill.md 让 Hermes 零成本生图生视频
> **对你项目的价值**：WorkBuddy 同样可用免费模型 + Skill 做生图生视频（如跨境商品图、营销图），零成本

## 核心逻辑

- **文本大模型**：靠外部端大模型转为 API（即 0 token 方法）
- **生图 / 生视频**：靠一个 **Skill.md 文件**（标准格式，通用，可用于 Hermes / OpenClaw / Codex 等一系列客户端）

## 实测

1. Hermes 用零 Token 的 **DeepSeek** 大模型，先让它**收集今日美股行情**（模拟平时调用工具采集数据的场景，数据是真实的昨日周五收盘记录）
2. 指令：「生成一个图片，保存在指定位置」
3. AI 自动触发刚才那个 Skill → 自己整理文生图提示词 → 用浏览器智能化技术把提示词**注入到 Web 大模型** → 把生成结果存到对话里指定的桌面位置
4. 打开生成的图：排版、美观度、重要信息表达都「还可以」

## 与你项目的关系

- 扩展「0 token 方法」的边界：不只是文本 Agent，连**生图生视频也能零成本**——前提是配好对应的通用 Skill。
- 对 WorkBuddy：跨境业务里可用免费模型 + 生图 Skill 批量产出商品图、营销海报、社媒配图，全程不耗 Token。
- 关键机制：Skill.md 是跨客户端通用的，你在一个地方写好生图 Skill，Hermes / WorkBuddy / OpenClaw 都能复用。
