---
title: "V23-HermesEngine用智谱网页模型代替API"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/ZMKC78tPrLI/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~60s"
date: "2026-08-10"
tags: ["抖音学习", "零Token", "HermesEngine", "智谱GLM", "网页大模型转API", "配置", "WorkBuddy", "提炼"]
quality: "★★★★☆"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/ZMKC78tPrLI/`
> **转录引擎**：whisper-small｜**视频时长**：约 60 秒
> **质量评分**：⭐⭐⭐⭐☆（Hermes Engine 用智谱网页模型代替 API 的最完整点击路径，已整理成指南）
> **可复用部分**：Hermes Engine 添加供应商 → 登录网页端 → 代理/地址配置 → 生成 API Key → 填 Base URL + 模型名 的全流程
> **对你项目的价值**：把智谱 GLM 的免费网页额度接进客户端（Hermes / WorkBuddy）的标准操作步骤

## 实操步骤（已纠正音译）

1. 装好 Hermes Engine（Windows 用安装包），设置里把语言改为**简体中文**
2. 点「供应商」→ 添加大模型，以**智谱**为例，点下一步
3. 点 **OAuth 登录方式**打开登录，像登智谱官网一样登录
4. 登录后点「添加账号」，已有一个智谱账号
5. 点左侧「设置」→「代理设置」，绑定地址**自己用默认即可**
6. 点左侧「API Key」→ 打开认证 → **新建一个 API Key**（名称与 Key 自动生成）
7. 点进 API 的 **Base URL**（填上面那个地址），**模型名称**填下面那个
8. 打开 **Hermes**，输入模型切换命令，翻到「**自定义介入 API 的方式**」点进去
9. 把 **Base URL** 和 **API Key** 复制过去 → 回车 → 查看所有可用 API 模型
10. 结果：智谱的 **GLM** 模型全部出现 ✅

## 与你项目的关系

- 这是「0 token 方法」接**智谱 GLM** 的具体落地（Hermes Engine 侧）。整条链路：登录网页端 → 生成 API Key → 填 Base URL + 模型名 → 自定义 API 接入。
- 对 WorkBuddy：WorkBuddy 的自定义 API 字段（Base URL / Key / 模型名）与这里一一对应，把智谱免费网页额度按同样字段填进 WorkBuddy 即可零成本用 GLM。
- 视频作者已把完整操作整理成指南，需要时可在其评论区索取。
