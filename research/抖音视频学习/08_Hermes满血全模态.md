---
source: "抖音 @李君陌"
url: "https://v.douyin.com/vA6GS2t6bn8/"
date: 2026-08-04
tags: [Hermes, 多模态, 生图, 生视频, 扩展]
confidence_level: B
source_type: third_party
---

# 把你的hermes打造成满血全模态~生图+生视频+...

## 核心内容（282字）

如何将 Hermes Agent 从纯文本模型升级为多模态 Agent，使其具备图像生成、视频生成等能力。核心思路不是等待 Hermes 内置多模态，而是通过 MCP 服务器和外部工具集成来实现。视频演示了如何配置 Hermes 连接 Stable Diffusion / ComfyUI（生图）、连接视频生成 API（生视频）、以及利用视觉模型进行图像理解。通过插件和 MCP 扩展，Hermes 可以成为多模态任务的统一调度中心。

## 关键操作步骤

1. **生图集成**：通过 MCP 连接 ComfyUI / Stable Diffusion API
2. **生视频集成**：连接视频生成 API（如 Runway、Pika）
3. **视觉理解**：配置 auxiliary.vision 使用视觉模型（GPT-4V / Claude Vision）
4. **统一调度**：让 Hermes 根据任务类型自动路由到对应的多模态工具
5. **工作流编排**：设计图→文→视频的多步创作工作流

## 适用场景
- 需要 Hermes 具备图像/视频处理能力的用户
- 内容创作者和多媒体工作者

## 注意事项
- 多模态工具需要额外的 API Key 和计算资源
- 视频生成对硬件要求较高