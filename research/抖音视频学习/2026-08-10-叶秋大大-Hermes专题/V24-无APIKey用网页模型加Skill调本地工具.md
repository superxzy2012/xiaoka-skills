---
title: "V24-无APIKey用网页模型加Skill调本地工具"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/QIOy6AFlwIo/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~80s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "Hermes", "Skill", "XML", "本地工具调用", "网页大模型", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/QIOy6AFlwIo/`
> **转录引擎**：whisper-small｜**视频时长**：约 80 秒
> **质量评分**：⭐⭐⭐⭐⭐（正面解决「网页模型不能调工具」的痛点：用 Skill.md + XML 格式让无 API Key 也能调本地工具）
> **可复用部分**：上传 Skill.md 让网页模型输出标准 XML → 工具调用；右上角两开关（自由切模型 / 调工具）；本地读文件 / 读表 / 生成文件的实测
> **对你项目的价值**：WorkBuddy 接免费网页模型后也能稳定调本地工具（读文件、跑表、生成文件），无需任何 API Key

## 原理与痛点

用网页端大模型代替 API 的缺点是**不能调用工具**；用 **XML 模拟标签形式**弥补了这一缺点。

## 解决方法

1. 上传一个作者做好的 **Skill.md 文件**，作用是让网页大模型输出**标准的 XML 格式**去调用工具
2. 借助 Claude / Cloud Code 等 API 助手把该文件替换上去
3. 重新加载客户端，UI 右上角打开两个开关：
   - **可以自由切换模型**
   - **调用工具的开关**

## 实测

- 指令「查看本地文件」→ 工具调用启动，输出文件内容正确（连隐藏 / 系统文件也展示）
- 测试「打开文件里某张表格查内容」→ 查出真实内容，与表内一字不差
- 测试「让网页大模型生成新文件」→ 调用了 pandas 类函数，本地出现对应 sheet 的表，内容正确
- **全程未使用任何 API Key** 即实现本地工具调用 ✅

## 与你项目的关系

- 这是「0 token 方法」在**工具调用**上的关键补完：免费网页模型 + Skill.md（标准 XML 输出）+ 工具开关 = 无 Key 也能跑本地工具链。
- 对 WorkBuddy：WorkBuddy 同样支持 Skill 机制，可复用这套「Skill.md 驱动标准 XML 工具调用」的做法，让免费模型承担读文件、处理表格、生成文件等真实任务。
- 与 V22（注入提示词 + XML 解析）是同一思路的不同落地，互为印证。
