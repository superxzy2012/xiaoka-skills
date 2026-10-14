---
title: AI破甲工具箱 集成主流IDE编程软件
source: douyin
type: 图文
author: 灯博汇照明：邹'R
note_id: "7662305546372883560"
url: https://www.douyin.com/note/7662305546372883560
published: 2026-07-14
date: 2026-09-30
tags: [抖音, 图文, AIIDE, 越狱, 破解, 规则注入, Claude-Code, Cursor, Trae, Codex, 风险]
confidence: A
---

# AI破甲工具箱：集成主流 IDE 的「破甲/规则注入」工具

## 这是什么（A 级，直接读画面）
第三方 **Windows 桌面工具「AI破甲工具箱」v1.1**，定位「AI IDE 破甲指令与逆向技能管理」。本质：
- **破甲**：向各 AI 编程工具本地配置目录**注入自定义指令/规则**，作者称可「解除约束」，支持一键激活与干净撤销（各插件独占管理规则文件）。
- **逆向技能**：装载/移除第三方提示词或规则包，支持单项目「换装」切换。
- **共享技能池 / 在线更新**：默认从 **Gitee（码云）** 仓库拉取技能与 version.json，token 自动从 git remote 解析，可用环境变量 `GITEE_TOKEN` 覆盖。
- **技术栈**：Python 3.12 · PySide6(Qt) · PyInstaller 打包。

## 支持的 IDE（官方“关于”页，共 8 款）
| IDE | 全局规则路径（示例机） |
|---|---|
| Claude Code | `~\.claude` |
| Claude Code Haha | `~\.claude` |
| Codex CLI | `~\.codex` |
| CodeBuddy CN | `~\.codebuddy\rules` |
| Trae（国际版） | `~\.trae\rules` |
| Trae CN | `~\.trae-cn\rules` |
| Cursor | `~\.cursor\rules` |
| Qoder | （对应规则目录） |

> 文案还提到 ChatGPT 5.6、WorkBuddy 等。示例机共扫到 25 个配置目标（11 已激活 / 12 未激活 / 2 未安装）。

## 核心功能
1. 自动扫描本机 AI IDE 的安装/破甲/规则状态（可手动「重新检测」）。
2. 全局一键破甲 / 撤销破甲，「破甲全部未激活」批量处理。
3. 技能装载、移除、单项目换装。
4. 手动「+添加项目」或自动识别常见目录（`G:/Projects`、`~/code`），支持全局 + 单项目分级配置。
5. 在线更新（本体 + 技能包，默认 Gitee 源）；内置教程（F2）、关键词搜索。

## 🔴 风险判断（重要，故不做安装封装）
- 属**第三方破解/越狱类工具**，会**篡改已安装 AI 编程工具的本地文件**，可能违反对应软件用户协议，导致**账号封禁、服务失效**。
- 「解除约束」注入可能**绕过模型安全策略**，产出不受控；此类工具也常被捆绑木马/后门，来源与签名不透明。
- 更新依赖 Gitee 私有仓 + 自动读取本地 git 凭据，存在**凭据与供应链安全**隐患。
- 合规/安全替代：用各 IDE **官方支持的自定义规则/指令机制**（如 Claude Code 官方 rules/skills、Cursor 官方 rules）来配置偏好，无需「破甲」。

## 图集（3/4，第4张为同界面补充）
![工具箱主界面](../attachments/20260714-7662305546372883560/g01.webp)
![关于窗口](../attachments/20260714-7662305546372883560/g02.webp)
![在线更新窗口](../attachments/20260714-7662305546372883560/g03.webp)

## 原文文案
> AI破甲工具箱 集成主流IDE编程软件。支持chatgpt 5.6，Trae国际版，Trae CN，Claude Code，Cursor，Qoder，CodeBuddy，WorkBuddy。
