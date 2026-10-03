---
title: "V12-协议转换工具免Token用GLM"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/CCeqRNlHdbE/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "协议转换", "GLM", "Hermes", "Windows", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/CCeqRNlHdbE/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（给出另一套「免 Token 用 GLM」的协议转换路径，并实测工具调用）
> **可复用部分**：协议转换保证响应规范 + 命令切换所有网页大模型 + Hermes 引擎调用工具实测
> **对你项目的价值**：又一种「0 token 接 GLM」的实现，且验证了在 Windows 上也能稳定跑（你 Mac 更没问题）

## 核心路径

通过**协议转换工具**（视频口播模糊，疑为某 F 系工具）做协议转换，保证响应规范，从而**免 Token 使用 GLM**。作者针对 Windows 用户运行中的三类报错做了整理与修复，已能零报错运行。

## 关键点

- 在 **Hermes 引擎**（视频称 hermis engine）里使用免 Token 的 GLM，仅图标可能导致乱码
- 用**协议转换命令**可自由切换所有网页端大模型
- 实测「调用工具能力」：问「今天重庆天气如何」——该问题至少需要调用两个工具（拆解日期 + 对应地点天气），结果正确报出了日期与天气

## 与你项目的关系

- 与 V10（OpenClaw）、V13/V14（网页大模型转 API 工具）并列，是「0 token 方法」的**多种可选实现之一**。不同工具覆盖不同模型 / 平台，可互为备份。
- 实测证明：**免 Token 模型接入客户端后，工具调用（多步、需拆日期/查天气）依然正常**——打破"免费模型不能调工具"的顾虑。
- 对 WorkBuddy：任选一种协议转换 / 反代工具，把 GLM 等免费网页模型转成标准 API，挂进 WorkBuddy 自定义 API 即可，Mac 环境比视频里的 Windows 更顺。
