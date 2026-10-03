---
source: "抖音 @李君陌"
url: "https://v.douyin.com/0U8FseFvc0U/"
date: 2026-08-04
tags: [Hermes Agent, 入门, 新手技巧]
confidence_level: B
source_type: third_party
---

# 新手装完Hermes Agent先学这5招~

## 核心内容（283字）

Hermes Agent 安装完成后，新手最需要掌握的 5 个核心技巧。Hermes Agent 是一个开源 AI Agent 框架，支持多种 LLM 后端、具备记忆系统、技能系统和多平台网关。视频从实际操作角度出发，演示了：如何切换模型提供者、如何编写和加载自定义技能、如何利用记忆系统让 Agent 记住上下文、如何配置飞书/Telegram 等多平台接入、以及如何用 cron 定时任务实现自动化。这些技巧是充分发挥 Hermes 能力的基础。

## 关键操作步骤

1. **模型切换**：使用 `/model` 命令或编辑 config.yaml 切换 LLM 后端
2. **技能编写**：创建 `~/.hermes/skills/<name>/SKILL.md` 自定义技能
3. **记忆管理**：使用记忆工具持久化重要信息，跨会话复用
4. **多平台接入**：配置 channels 段连接飞书、Telegram 等
5. **Cron 任务**：使用 `hermes cron` 设置定时执行的任务

## 适用场景
- 刚完成 Hermes Agent 安装的新手用户
- 想要充分发挥 Hermes 能力但不知道从何入手

## 注意事项
- 技能编写需要遵循 YAML frontmatter 规范
- 多平台接入需要各平台的应用凭证