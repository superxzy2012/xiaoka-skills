---
title: "如何让Pi上也可以用上WorkBuddy的免费额度"
source_url: "https://v.douyin.com/04EM85i2OUI/"
platform: douyin
作者: "小马哥早点睡觉"
入库日期: 2026-09-26
tags: [提炼, 抖音, workbuddy2api, CodeBuddy, 反代网关, 账号池, 免费额度]
added_by: 小豆
summary: "开源项目 workbuddy2api：腾讯 CodeBuddy 账号池管理控制台 + OpenAI 兼容反代网关，让第三方客户端（含 Pi）用上 WorkBuddy/CodeBuddy 免费额度。"
置信度: A
---

# workbuddy2api：让 Pi 用上 WorkBuddy 免费额度

## 核心内容

介绍刚开源的项目 **workbuddy2api**：把腾讯 CodeBuddy（WorkBuddy）账号做成**账号池 + OpenAI 兼容反代网关**，任何支持 OpenAI 接口的客户端（标题点名 Pi）填该网关地址即可调用免费额度。

## 核心要点（经截帧 OCR 核实）

| # | 要点 | 说明 |
|---|------|------|
| 1 | **OpenAI 兼容反代网关** | workbuddy2api 主体，把 CodeBuddy 账号接口转成标准 OpenAI 协议，第三方客户端直接对接 |
| 2 | **WorkBuddy Manager 管理控制台** | 配套 Web 管理端：扫码批量纳管账号、自动签到、密钥分发、IP 管控、调用日志与用量统计，一个面板搞定 |
| 3 | **刚开源·MIT 许可** | 口播"昨天才刚发布第一次开源"；源码随发布包分发（MIT），已部署实例不受重装影响 |
| 4 | **技术栈** | React 19 + TypeScript + Tailwind CSS（前端）；FastAPI 0.115+ / Python 3.11+（后端）；支持 Docker、Windows 本地启动脚本、子路径部署（PR #72 已补齐"反代保留前缀"） |
| 5 | **发布社区** | LINUX O 社区交流（画面显示约 4,048 stars / 25 forks） |

## 与我们现有体系的关系

- 与本机 **Chat2API 8080 + llm_retry_proxy 8081** 属同类"账号池反代"思路，区别是上游为腾讯 CodeBuddy
- 若 CodeBuddy 免费额度稳定，可作为 OmniRoute/combo-gw 之外的**备用免费通道**

## 可执行 Takeaway

- [ ] 在 LINUX DO / GitHub 定位 workbuddy2api 仓库（OCR 未见完整 URL → **待核实**，搜索关键词 `workbuddy2api`）
- [ ] Docker 部署 + 扫码纳管 1-2 个 CodeBuddy 账号，验证反代链路和免费额度可用性
- [ ] 跑通后评估是否接入 OmniRoute 作为备用 provider，再决定是否封装技能

## 完整口播转写（原文 15 秒）

> 终于有人做了这个 WorkBuddy 的反代工具了。除了反代的功能，它还有自动签到，还有批量管理账号的功能。昨天才刚发布的，刚开源，第一次就（指刚开源第一次分享）。

> 注：Whisper 原始识别为"Vocabody/自动前道/必量管理"，已据截帧 OCR 更正为"WorkBuddy/自动签到/批量管理"。

## 关键帧

![[attachments/20260926-04EM85i2OUI/f_01.png]]
![[attachments/20260926-04EM85i2OUI/f_02.png]]
![[attachments/20260926-04EM85i2OUI/f_03.png]]
