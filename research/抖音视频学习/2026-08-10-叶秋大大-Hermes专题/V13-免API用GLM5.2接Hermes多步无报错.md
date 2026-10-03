---
title: "V13-免API用GLM5.2接Hermes多步无报错"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/Emo3hOtqtjA/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "GLM5.2", "Hermes", "网页大模型转API", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/Emo3hOtqtjA/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（用一连串连续任务证明免 API 的 GLM 5.2 接客户端稳定无报错）
> **可复用部分**：「网页大模型转 API 工具」的开关式操作（左按钮 + 右运行）+ Hermes 接入链路
> **对你项目的价值**：证实 GLM 5.2 免 API 接 Hermes 后，连续多步任务无「刷新界面」报错中断

## 核心方法

既不用 API、又能用 **GLM 5.2**，且无任何报错。准备工作：打开**网页大模型转 API 工具**，开左侧按钮、点右侧运行；再用 **Hermes** 把这个免 API 的 GLM 5.2 接进去。

## 实测（一连串连续任务）

1. 问电脑上某个不认识的文件是干什么的 → 答「空文件、零字节，建议删除」
2. 追问「查看里面内容」→ 正常读内容
3. 下达「执行删除」→ 完成

整个过程**没有出现「刷新界面」之类的报错弹窗**，证明免 API 技术升级成功。

## 与你项目的关系

- 这是「0 token 方法」接 **GLM 5.2** 的具体验证：免费网页端 GLM 经转 API 工具反代后，作为零成本模型挂进客户端（Hermes / WorkBuddy）稳定可用。
- 关键价值：**连续多步任务不中断**——之前网页大模型转 API 常被「需要刷新 / 重新登录」打断，本集证明已解决。
- 对 WorkBuddy：可把 GLM 5.2（智谱免费额度）经同类转 API 工具接进 WorkBuddy 自定义 API，作为零成本主力或兜底模型。
- 与 V14 同源（都讲 GLM 5.2 免 API 接 Hermes），V14 进一步演示了更深的连续工具调用。
