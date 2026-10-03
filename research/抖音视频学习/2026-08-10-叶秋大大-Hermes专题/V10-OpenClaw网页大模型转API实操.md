---
title: "V10-OpenClaw网页大模型转API实操"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/E0Arlj9S9-4/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~90s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "OpenClaw", "网页大模型转API", "Hermes", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/E0Arlj9S9-4/`
> **转录引擎**：whisper-small｜**视频时长**：约 90 秒
> **质量评分**：⭐⭐⭐⭐⭐（给出最关键的「网页端大模型 → 标准 API」具体工具与四步法，可操作性强）
> **可复用部分**：OpenClaw 的四步安装 + 扫码登录网页端 + 启动 gateway 的完整路径
> **对你项目的价值**：这就是你要找的「0 token 方法」核心实现之一——把豆包 / Kimi / DeepSeek 等网页端免费模型，经 OpenClaw 反代为标准 API 接进 WorkBuddy

## 核心逻辑

通过 **OpenClaw（视频误称「龙虾」）** 这个工具，把网页端大模型（免费、不费 Token）转成底层的标准 API 形式，直接消解「Token 焦虑」。

## 四步实操（已纠正音译）

1. **安装**：作者提供了现成安装脚本，逐条复制粘贴执行即可（不会装也没关系）
2. **配置认证**：执行脚本后自动弹出豆包 / Kimi / DeepSeek 等**网页端**，用手机扫码或登录完成验证
3. **起一个轮询代理**：此后使用不再需要手机验证 / 扫码（网页端 AI 使用本身不费 Token）
4. **启用 OpenClaw gateway**：重新开一个终端执行启用命令，自动弹出 OpenClaw 界面；用**斜杠命令**查看当前可用的大模型（注意：这些模型名比普通 API 调用的名字多了一个后缀，如 `DeepSeek-GlobalWeb`、`Grok-GlobalWeb` 之类）

## 实测

- 在 OpenClaw 对话框输入「做一个弹球游戏」，约两分钟生成可玩链接，一次成型
- 证明该方法既能完成任务、又不费任何 Token

## 与你项目的关系

- 这是「0 token 方法」最直接的落地工具之一：OpenClaw 负责把**免费网页端模型**转成标准 API，WorkBuddy（同 Hermes / OpenClaw 这类 OpenAI 兼容客户端）直接按自定义 API 调用即可。
- 关键点：网页端登录一次后由代理维持会话，**无需反复扫码**，适合做长期常驻的零成本模型服务。
- 接 WorkBuddy 时，把 OpenClaw gateway 暴露的本地端点 + 对应模型名（带后缀）填进 WorkBuddy 的自定义 API 即可。
