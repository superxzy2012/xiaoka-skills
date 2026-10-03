---
title: "懒人 Hermes 多 Agent 体验：多分身（Profile）配置流 + QQ/飞书双平台对接"
source: "https://v.douyin.com/zUAx6d-xDd4/"
platform: douyin
type: image-text
author: "諸星hanabi"
published: 2026-06-10
captured: 2026-08-30
tags: [douyin, 提炼, Hermes, 多Agent, Profile, 分身隔离, QQBot, 飞书, 网关]
summary: "三图讲透 Hermes 多 Agent 落地：① profile 分身三步走（create / model / gateway start）+ 共享与隔离边界；② QQ Bot 独立对接的 3 优势 3 深坑（公域不推群消息、open 策略 + ALLOW_ALL_USERS=false 会强制自锁、共用 default 进程会牵连飞书掉线）；③ QQ 私聊 vs 飞书群聊双平台定位与关键配置（FEISHU_ALLOW_BOTS=mentions）。"
---

# Hermes 多 Agent 体验：多分身 + 双平台对接

> [!abstract] 摘要
> 抖音图文 3 张（諸星hanabi）：把 Hermes 多 Agent 落地的实操经验讲透了——**profile 分身怎么建、共享什么隔离什么**、**QQ Bot 对接的 3 个深坑**、**QQ 私聊与飞书群聊双平台如何共存**。核心结论：双平台对接必须用 profile 分身部署，把 default 留给工作群。

> ⚠️ **方法说明**：图文内容通过 macOS Vision 框架本地 OCR 提取（`/Users/【BOSS英文名】/WorkBuddy/Claw/scripts/vision_ocr`），OCR 识别有误的字已据语义还原并标注。

---

## 图 1 · Hermes 极简多分身（Profile）配置流
> 副标题：多 Agent 独立共存与数据隔离·核心指南

![[20260830-hermes-profile-01.jpeg]]

### 三步建立隔离分身

| 步骤 | 命令 | 作用 |
|---|---|---|
| 01 建立隔离分身 | `hermes profile create <名字>` | 一条命令创建完全独立的 Agent，配专属工作环境 |
| 02 独立配置模型 | `hermes -p <名字> model` | 进入该分身工作空间，独立指定大模型与凭证 |
| 03 启动独立网关 | `hermes -p <名字> gateway start` | 后台静默拉起该分身**独立的 IM 消息网关进程** |

### 分身切换与对话
```
hermes -p <名字> chat
```
- 不加 `-p` 标记时，系统自动默认调用 `default` 分身

### 多分身共享了什么？（关键边界）

**共享（不隔离）：**
1. **全局 CLI 骨架**——使用同一个全局二进制包，不需要多次复杂部署
2. **系统环境变量**——若分身内部 env 为空，则自动向上继承系统的全局凭证
3. **本地底层工具链**——共享宿主机上的 Docker 容器实例或本地 venv 工具库

**隔离（完全独立）：**
- 各个分身的**配置参数、专属记忆（Memory）及历史会话**均完全隔离独立

> 💡 **经验之谈**：平时调试优先使用 `hermes profile list` 查验分身状态！

---

## 图 2 · Hermes-QQBot 独立对接优势与巨坑
> 副标题：跑在 QQ 官方公域协议下的指令终端实践笔记

![[20260830-hermes-profile-02.jpeg]]

### ✅ PROS 独立适配的优势

1. **极简的指令终端**：支持 1-on-1 私聊极速连接。作为个人"高权限赛博保镖"非常合适，执行系统级高优指令极其敏捷
2. **安全事件完全隔离**：私聊不涉及复杂的群内广播与越权。只响应特定白名单用户的指令，消息不污染其他办公协作环境
3. **本地自锁保护机制**：当配置存在风险（如公域敞开但无白名单）时，网关会自动锁死拒绝启动，提供物理级别的防刷保护

### ❌ CONS 必须避开的深坑

1. **公私域事件推送阻碍**：公域 Bot **默认不推送普通群聊消息**。如果非要拉进群，必须在腾讯后台把该群**绑定为测试白名单**，否则接收不到包
2. **未对齐时的一枪自锁**：默认配置下，若 QQ 策略设为 `open` 且 `QQ_ALLOW_ALL_USERS=false`，系统会在**初始化时强制拉闸拒绝启动**
3. **共用进程断线牵连**（最坑）：若与飞书共用同一个 `default` 进程，一旦 QQ 端的冲突引发自锁重启，**会把隔壁本已在线的飞书网关一并拔线挂起**

> ⚠️ **建议**：私聊终端建议使用 `mybot` **专属分身**进行隔离保护，把 `default` 留给工作群！

---

## 图 3 · Hermes 双 Agent 平台对接指南
> 副标题：同服务器下多网关隔离与群聊对账不踩坑指南

![[20260830-hermes-profile-03.jpeg]]

### QQ 独立私聊（QQBOT） VS 飞书协作群聊（FEISHU）

| | QQ 独立私聊 | 飞书协作群聊 |
|---|---|---|
| **平台定位** | 极简指令 | 多模协作 |
| **配置** | `open` 策略 + 允许所有，跑在腾讯官方公域协议下 | 配置群组策略，拉入多智能体群聊 |
| **用途** | 敏感告警 + 一对一高优系统指令执行 | 多 Agent bot-to-bot 协作窗口，处理复杂项目级对账测试 |
| **核心痛点/关键** | **公私域壁垒**：腾讯官方严格限制公域，非白名单绑定的普通 QQ 群，群聊消息默认无法被网关事件循环捕获，必须单点对齐 | **群安全策略默认 `allowList`（白名单制）**。必须在 `.env` 中正确指定 `FEISHU_ALLOW_BOTS=mentions` 才能在群里接收并响应被 @ 的消息 |

> 💡 **经验之谈**：双平台对接时，采用 `hermes profile` 分身部署可实现配置与数据完全隔离！

---

## 🔴 与 BOSS 现有体系的对账（重点）

> 这条图文几乎是在描述 BOSS 自己的环境，逐条对上了：

| 图文结论 | BOSS 环境现状 | 状态 |
|---|---|---|
| 飞书群需 `FEISHU_ALLOW_BOTS=mentions` | 2026-08-13 已给诸葛亮（CN Hermes）加 `feishu.allow_bots: mentions` | ✅ **已做对，图文印证** |
| 不要共用 `default` 进程，否则一端自锁牵连另一端 | 小豆用独立保活脚本 `/tmp/hermes_gateway_v0205_guard.sh`（精确匹配小豆 gateway 路径，不碰诸葛亮 CN gateway） | ✅ **已隔离，做法正确** |
| 双实例应走 profile 分身隔离 | 现状：小豆与诸葛亮是**两个完全独立的 Hermes 实例**（`~/.hermes/` 两套、`app_id` 不同），比 profile 分身隔离度更高 | ✅ 已满足（隔离更彻底） |
| `hermes profile list` 查分身状态 | 未用过，可作为日常巡检手段 | 🔵 待引入 |
| QQ Bot 接入方案 | 尚未接入，图文给了完整避坑清单 | 🔵 机会点 |

### 新增可用手法（BOSS 环境还没用的）
1. **`hermes profile list`** 作为分身/网关巡检命令，可并入 `13bots` 健康巡检或日常晨报
2. **QQ 私聊终端**作为个人"高权限赛博保镖"：适合 BOSS 用手机给 agent 下敏感/高优系统指令（相比飞书群更安全，私聊不污染协作环境）
3. 若未来接 QQ Bot：**必须建专属 profile 分身**，绝不能挂 `default`，且注意 `open` + `ALLOW_ALL_USERS=false` 的组合会直接拒绝启动

---

## 来源
- 抖音链接：https://v.douyin.com/zUAx6d-xDd4/
- 原图文 ID：76793987【手机号】（note 类型）
- 作者：諸星hanabi
- 图片数：3 张（1440×1440）
- 抓取时间：2026-08-30 07:41
- 提取方式：短视频下载器（redfox API）+ macOS Vision OCR
- 落库目录：`08-抖音视频学习/`

> ⚠️ **下载踩坑**：yt-dlp（2026.07.04）**不支持抖音图文帖**（`/note/` 类型 URL 报 `Unsupported URL`），必须用 `video-downloader` 技能的 redfox 解析。文件默认落到 `~/Downloads/QoderVideos/`（`photo_unknown_N.jpeg`）。
