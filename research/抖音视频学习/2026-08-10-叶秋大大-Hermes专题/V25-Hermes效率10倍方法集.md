---
title: "V25-Hermes效率10倍方法集"
author: "叶秋大大 (yeqiudada)"
source: "https://v.douyin.com/v28QK6Ckn_E/"
platform: "抖音"
transcript_engine: "whisper-small"
duration: "~90s"
date: "2026-08-10"
tags: ["抖音学习", "Hermes", "效率技巧", "WSL2", "YOLO", "Gateway", "飞书", "Docker", "WorkBuddy", "提炼"]
quality: "★★★★★"
---

> **作者**：叶秋大大（yeqiudada）｜**来源**：抖音 `https://v.douyin.com/v28QK6Ckn_E/`
> **转录引擎**：whisper-small｜**视频时长**：约 90 秒
> **质量评分**：⭐⭐⭐⭐⭐（Hermes 提效技巧合集，其中「Gateway 连飞书/微信 + 定时任务」与你需求直接相关）
> **可复用部分**：WSL2 环境 / 回滚 / YOLO / 命令组合 / Gateway 接飞书微信 + 定时 / Docker 部署 / 嵌入产品
> **对你项目的价值**：你已连上飞书——Hermes Gateway 可接飞书并加定时任务，这条思路可迁移到 WorkBuddy 的自动化

## 七条提效方法（已纠正音译）

1. **Windows 走 WSL2 虚拟环境**：直接开 PowerShell 跑 Hermes 会报错，务必在 WSL2 里跑
2. **提前开 Rollback（回滚 / 后悔药）**：改错改乱可直接回到上一个提示点
3. **YOLO 命令（危险）**：解除 AI 的约束锁，无需你确认即可自作主张——慎用
4. **好用的命令组合**：写 Python 脚本时用某命令发任务、用某命令指定用哪个大模型；会话断了要恢复对话 + 加新技能，一条命令完成；只要纯净最终答案用某命令（适合脚本调整过程）
5. **Hermes Gateway 连飞书 / 微信 + 定时任务**：连上后加定时任务，就能**定时发邮件 / 发消息 / 推送资料**
6. **跑在 Docker 容器里**：可指定不同容器镜像，多容器隔离
7. **嵌入自己产品**：把 Hermes 嵌入自己的发送程序，做自己的产品

## 与你项目的关系

- **第 5 条与你强相关**：你已连上飞书，Hermes 的 Gateway 思路（接飞书 + 定时推送）可直接对照——WorkBuddy 这边你已能从飞书发指令、跨端同步，后续若要「定时把选品报告推到飞书」，架构上完全可行。
- WSL2 / 回滚 / YOLO / Docker 这些属于 Hermes 运维技巧，你若用 WorkBuddy 做 OPC 一人公司的 agent 蜂群，环境隔离（Docker）和回滚机制都值得借鉴。
- 提醒：YOLO 类「免确认自动执行」命令风险高，生产环境建议保留人工确认，尤其涉及文件删除 / 对外发送时。
