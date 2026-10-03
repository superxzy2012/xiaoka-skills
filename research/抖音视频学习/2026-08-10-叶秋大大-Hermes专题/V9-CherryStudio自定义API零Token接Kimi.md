---
title: "V9-CherryStudio自定义API零Token接Kimi"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/uvbYB3dDmnM/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "CherryStudio", "Kimi", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/uvbYB3dDmnM/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（步骤清晰，但与 V8 高度重合，仅作互补印证）
> **可复用部分**：Cherry Studio「自定义 API」接入免费网页模型的完整点击路径
> **对你项目的价值**：确认「网页端免费模型 → 标准 OpenAI 兼容 API → 客户端调用」范式，可映射到 WorkBuddy 的自定义提供商入口

## 核心方法

用 **Cherry Studio** 的「自定义 API」功能，把**免费网页端大模型**（本集演示 Kimi K2）伪装成 OpenAI 兼容接口，零 Token 调用。

## 实操步骤（已纠正 whisper 音译）

1. 设置 → 添加供应商 → 选 **OpenAI**（接的是零 Token 的免费服务，供应商名字任意取）
2. 下拉选 **自定义 API**
3. 去平台控制台复制 **Base URL** 和 **API Key**，分别粘贴进对应字段
4. 模型名填 **Kimi K2**（口播误识别为 K3）
5. 点「检验测试」确认连接成功 →「获取列表」可看到所有零 Token 模型及其能力（工具 / 推理 / 视觉均有图形标识）

## 实测

- 用 Kimi K2 在本地桌面**新建 TXT 文件**（成功）
- 让其**分析一份股市大盘文档**并把总结写入该 TXT（成功，结构清晰，模仿分析师写法）

## 与你项目的关系

- 与 **V8 几乎同源**：V8 也是 Cherry Studio 自定义 API 接 Kimi 写桌面文件、分析 A 股；本集是同一套流程的更简洁版，差异仅在更强调「获取模型列表 / 检验测试」的点击细节。
- 范式确认：**Hermes / Cherry Studio / WorkBuddy 这类 OpenAI 兼容客户端都支持「自定义提供商 + Base URL + API Key」**。把免费网页端模型（硅基流动 / Kimi / 智谱）的额度经「网页大模型转 API」反代后，即可作为零成本模型挂进 WorkBuddy 作兜底。
- 视频未贴清「自定义 API」的具体字段名，接 WorkBuddy 时需先在 WorkBuddy 里确认对应的自定义 API 字段。
