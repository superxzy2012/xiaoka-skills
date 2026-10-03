---
title: "Codex 零成本生图生视频 - Agnes AI Skill 接入方案"
date: 2026-09-06
source: 抖音
author: 叶秋大大
video_url: https://www.douyin.com/video/7675376【手机号】1
video_id: 7675376【手机号】1
tags: [Codex, AgnesAI, 生图, 生视频, Skill, 零成本, AI工具]
confidence: B
---

# Codex 零成本生图生视频 — Agnes AI Skill 接入方案

> 通过构建 Skill 的方式赋予 Codex 生图生视频能力，零成本让灵感直接变成内容

## 🎯 核心结论

**Codex（OpenAI 官方编程助手）本身只有 LLM 能力**，通过自建 **生图 Skill / 生视频 Skill** 接入 **Agnes AI** 免费模型（`agnes-image-2.0-flash` / `agnes-video-v2.0` / `agnes-2.5-flash`），可以实现零成本图像生成和视频生成。

架构：**Codex++ 导演层 → Skill 调度免费模型 → 图片/视频结果**

## 🏗️ 架构图

```
┌─────────────────────────────────────────┐
│              Codex++ 导演层             │
│         （仅接入 LLM 大语言模型）        │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
  生图 Skill      生视频 Skill
       │               │
       ▼               ▼
 Agnes Image     Agnes Video
 免费图像模型    免费视频模型
       │               │
       └───────┬───────┘
               ▼
        图片 / 视频结果
```

## 🔧 技术要点

### 模型列表（Agnes AI 提供）
| 模型名称 | 类型 |
|---------|------|
| `agnes-2.5-flash` | 通用多模态 |
| `agnes-2.5-pro` / `agnes-2.5-pro-alpha` | 通用多模态 Pro |
| `agnes-image-2.0-flash` | 图像生成 |
| `agnes-image-2.1-flash` | 图像生成 v2.1 |
| `agnes-video-v2.0` | 视频生成 |
| `agnes-2.0-flash` | 通用 v2.0 |

### 接入方式
1. **API 端点**：`https://apihub.agnes-ai.com/v1/`
   - 图像：`/chat/completions`（多模态方式）
   - 视频：`/videos/`（异步任务，提交后轮询）
2. **API Key**：通过 `AGNES_API_KEY` 环境变量传入
3. **安全存储**：macOS 钥匙串（`security add-generic-password -s "AgnesAI" -a "agnes-api-key" -w "xxx"`）
4. **本地代理**：`127.0.0.1:57321`（Codex++ relay）

### 生图流程
1. Codex 加载 Agnes Image 2.0 Flash Skill
2. 读取 `sample-prompts.md` 等参考文件
3. 运行 `image_gen.py generate --prompt "..."`
4. Skill 调用 Agnes API 生成图片
5. 返回结果给 Codex 展示

### 生视频流程
1. 提交视频生成任务到 `/videos/`
2. 返回 task ID（如 `task_PDCBHsRerzuVgXkntzi9DGjyKc4UHj5P`）
3. 轮询任务状态（30% → ... → 100%）
4. 任务完成后获取视频结果

## ⚠️ 已知问题

### ContextWindowExceededError
- **现象**：`The input (1754198 tokens) is longer than the model's context length (524288 tokens)`
- **原因**：Codex 把太多上下文（代码、文件内容）一起发给了 Agnes 模型
- **解决**：生图 Skill 应该只传 prompt，不要带整个代码库上下文
- **经验**：API Key 可以后续补充，不影响先生成

## 📎 附件

![帧01](../attachments/20260906-codex-free-image-video/frame_01.png)
![帧06](../attachments/20260906-codex-free-image-video/frame_02.png)
![帧16](../attachments/20260906-codex-free-image-video/frame_03.png)
![帧18](../attachments/20260906-codex-free-image-video/frame_04.png)
![帧22](../attachments/20260906-codex-free-image-video/frame_05.png)
![帧25](../attachments/20260906-codex-free-image-video/frame_06.png)

## 📝 补充说明

> 本视频为无声视频（无配音），内容全部来自 25 帧画面 OCR 识别。
>
> 视频作者在 Codex 中演示了从 Skill 安装 → 配置 API Key → 生成图片 → 生成视频的完整流程。
> 最终生成的蓝色小狗图片和视频效果"跟付费的差不多"。

## 🔗 相关链接

- Agnes AI 官网：https://agnes-ai.com
- API 文档：https://apihub.agnes-ai.com/
- Codex：OpenAI 官方编程助手
