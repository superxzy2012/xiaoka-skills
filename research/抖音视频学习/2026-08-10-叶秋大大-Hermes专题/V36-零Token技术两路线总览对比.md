---
title: "V36-零Token技术两路线总览对比"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/pJ88rSQ7zKI/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~113s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "OpenClaw", "网页大模型转API", "Flex网关", "总览", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/pJ88rSQ7zKI/`
> **转录引擎**：whisper-small｜**视频时长**：约 113 秒
> **质量评分**：⭐⭐⭐⭐⭐（全系列最值得先读的一篇——把「零 Token 技术」的两条路线、原理、工具调用机制一次性捋清）
> **可复用部分**：两条零 Token 路线的原理对比（OpenClaw / 网页转 API）+ 为何用 XML 而非 JSON + Flex 网关的多客户端接入
> **对你项目的价值**：这是整套「0 token 方法」的**地图**，先看这篇再看分篇，能少走很多弯路

## 两条零 Token 路线（都是独立产品，不是同一个东西）

### 路线 A：零 Token 的 OpenClaw（视频称「龙虾」）

- 形态：一个**重写的 AI Engine**（用 TypeScript 重写）
- **原理**：把登录网页端后的 **Cookie 保存下来**，调用时自动免认证调用
- **工具调用**：直接用 **XML 模拟标签**的方式调用（不是 JSON）
- 为什么用 XML 不用 JSON：JSON 在大模型传输过程中**格式容易被破坏**，XML 不会
- **优势**：已跟网页端大模型做好适配，你只需把提示词**写入 Skill.md 文件**即可

### 路线 B：网页大模型转 API（通用转换工具）

- 形态：一个**协议转换工具**，把外部端协议转成 **OpenAI 形式的标准 API 协议**
- 对接的客户端**各种各样，不限于 OpenClaw**
- 工具调用方法也不限一种；作者做法是加一层 **Flex 网关**，让多人调用能顺利进行
- **优势**：**灵活、不跟某一客户端绑定**——接入 OpenClaw 可以，接入 **Hermes**、**Cloud Code** 等也可以

## 与你项目的关系

- 这是全系列的方法论总纲。前 35 篇里反复出现的工具，在这里归了类：
  - **OpenClaw（龙虾）** = 路线 A，适合想直接用一个现成重写的 AI Engine、靠 Cookie 免认证
  - **网页大模型转 API + Flex 网关** = 路线 B，适合把免费网页模型转成标准 API 后，**接进任意 OpenAI 兼容客户端**（Hermes / WorkBuddy / Cloud Code）
- 对 **WorkBuddy**：你走的正是**路线 B**——把免费网页端大模型（智谱 GLM / Kimi / DeepSeek 等）经「网页大模型转 API」转成标准 API，挂进 WorkBuddy 的自定义 API，零成本调用。Flex 网关可选（多 agent 并发时用）。
- **XML 优于 JSON 做工具调用**这一点很关键：接 WorkBuddy 做工具调用时，优先用 XML 格式注入提示词（呼应 V22 / V24）。
- 下一篇建议看 **`00-零Token方法实施路径总览`**（小丽整理的全系列融合地图）。
