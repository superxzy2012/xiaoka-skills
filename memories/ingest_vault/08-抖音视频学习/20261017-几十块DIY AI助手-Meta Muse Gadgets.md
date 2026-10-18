---
title: "几十块DIY AI助手：ESP32 刷 Meta 开源固件接入 Muse"
original_title: "几十块DIY AI助手，外网杀疯了 最近 X 上刷屏的不是新手机，是一块几十块钱的 ESP32 开发板 🔥 我也入了一套，就几十块钱，估计这东西要涨价了。下一步接入muse和智能家居，想看什么玩法评论区告诉我！ #电子元件 #电子diy #diy电子爱好者 #ai #muse"
source_url: "https://v.douyin.com/Z0Q_fSZqabA/"
platform: douyin
douyin_id: "7697540721624641125"
author: "AI大脑洞"
duration: 73.7s
date: 2026-10-17
tags: [提炼, 抖音, ESP32, Muse, Meta, 开源硬件, DIY]
added_by: 小卡
status: 已核查
github_repo: facebookincubator/muse-gadget-sdk
---

# 几十块DIY AI助手：ESP32 刷 Meta 开源固件接入 Muse

> 🎬 抖音 · AI大脑洞 · 73.7秒 · 2026-10-17 入库
> 📌 转录由 AI 生成，专有名词已按官方仓库与媒体报道人工校对（校订处见下表）；如需引用请核对原视频。

## 🎯 一句话

Meta 于 2026-10-02 开源 **Muse Gadgets**（ESP32 固件 + Linux SDK，Apache-2.0），一块几十元的 ESP32 板刷上固件、配一个 SDK token，就能变成自家 AI 助手 **Muse** 的实体外设 —— 但 Muse 目前**只在美国开放**，token 限**个人非商用**，这才是视频没说的门槛。

## 📝 转录原文（已校对）

几十块钱的小板子，凭什么让 Meta 亲自下场？这两周它在推特上彻底杀疯了 —— Meta 开源了 Muse Gadgets，一块 ESP32 刷上固件就能接入自家的 AI 助手 Muse。关键推文将近 150 万浏览，一堆人跟着下单。有人把它做成不说话的 AI 小宠物，有人直接用中文跟它聊天。我也立马入了一套，几十块钱全套配齐，我估计很快就要涨价。

一共就五样东西，拼起来就是一个能听会说的 AI 助手：

1. **大脑** —— ESP32-S3 开发板，一排排引脚都能用代码控制输入输出，还自带 Wi-Fi 和蓝牙，连网接大模型全靠它；
2. **面包板加按键**，不用焊接，元件一插、跳线一连，电路就通了；
3. **耳朵** —— 麦克风模块，插上它写几行代码就能收到你的声音；
4. **嘴巴** —— 喇叭加音频功放，别看功放只有七个引脚，芯片输出的数字信号全靠它变成高频方波，推着喇叭发声；
5. **脸** —— 一块迷你 OLED 屏，能显示〔冷静的〕表情，有点小，我已经准备换个大点的了。

大脑、耳朵、嘴巴、脸，全齐了。下一步我要把它接入我家的智能家居。你最想让它帮你干嘛？评论区告诉我，呼声最高的下期直接做出来。

### 🔧 转录校订表（ASR 同音错字）

| 原转写 | 校订 | 依据 |
|---|---|---|
| 银角 | **引脚** | ESP32 引脚（GPIO），帧画面可见 `3V3/GND/EN/BOOT` 丝印 |
| 拿巴 | **喇叭** | 上下文「嘴巴」= 扬声器 |
| 工放 | **功放** | 音频功放模块，配合喇叭 |
| 高品方波 | **高频方波** | 功放把数字信号转成 PWM 方波驱动喇叭 |
| 接近我家的智能家居 | **接入** | 上下文语义 |
| 冷泽的表情 | 〔冷静的〕表情 | **存疑**，听感近似，无画面佐证 |
| 换开大胆了 | 换个大点的 | **存疑**，指换更大的屏 |
| ESP32S3 开发版 | ESP32-S3 开发板 | 板载丝印 `ESP32-S3-WROOM-1` |

## 💡 关键要点

- **项目本体**：`facebookincubator/muse-gadget-sdk`，Meta 超级智能实验室（MSL）出品，产品负责人 Nat Friedman 在 X 上宣布（2026-10-02）。仓库分 `esp32/`、`linux/`、`skills/`、`web-flasher/` 四个部分。
- **两条路线**：ESP32 Device SDK（用 ESP-IDF 6.0.1 编译烧写，做桌面小设备）；Linux Device SDK（树莓派 3B+/4/5/Zero 2W 等，装成 `musegadget` 后台服务，给 Muse 四个命令：`system.run` / `file.read` / `file.write` / `device.health`）。
- **接入四步**：① 在 gadgets.muse.ai 领 SDK token（每台设备一个）→ ② 刷固件/装服务 → ③ Muse App「设置 → 设备 → 开发者模式」添加 `MuseGadget-XXXXXX` → ④ 灯变蓝时按板载按钮确认本人，连 Wi-Fi 后变绿即完成。
- **官方板级配置 37 个**（其中 `sdkconfig.muse-*` 27 个），覆盖从「只有一颗指示灯」到「完整屏幕界面」；默认板是 **ESP32-C5 DevKitC-1**。
- **内网隧道**是真正的杀招：带 PSRAM 的板子能让 Muse 伸手进你家局域网，控制 Hue、Sonos、Apple TV、Nest 等本地 HTTP 设备 —— 这也正是视频结尾「接入智能家居」想做的事。
- **官方自己那台**叫 Muse Home Link：ESP32-C5、240MHz RISC-V、8MB PSRAM + 8MB Flash、Wi-Fi 6 双频、35×42×10mm，首批 5000 台免费给美国 Muse 订阅用户，**不可刷第三方固件**。

## 🔍 核查表（回源 GitHub API + 官方 README，2026-10-17）

| 视频说法 | 核实结果 | 依据 |
|---|---|---|
| Meta 开源 Muse Gadgets | ✅ 属实 | `facebookincubator/muse-gadget-sdk`，创建于 2026-10-02 |
| 一块 ESP32 刷固件接入 Muse | ✅ 属实 | 官方 `esp32/` Device SDK + SDK token 配对 |
| 关键推文「将近 150 万浏览」 | ⚠️ **无法回源** | X 浏览量无公开 API；媒体仅记 Nat Friedman 发帖「数小时内近 3 万浏览」，150 万未获独立佐证 |
| 「几十块全套配齐」 | ⚠️ **部分成立** | 板+屏+麦+功放+面包板确实几十元；但**还要美国区 Muse 订阅**才连得上，这部分成本视频没算 |
| 用的是 ESP32-S3 | ✅ 支持 | 官方默认板是 ESP32-C5 DevKitC-1，S3 在支持列表内（waveshare-s3 系列等） |
| 仓库热度 | ★ **2,254** / fork 475 | GitHub API 实时取数；最近提交 2026-10-16（PR #223），**在活跃维护** |
| 许可证 | **Apache-2.0** | README 明确；例外：Jollybot 头像不适用，minimp3(CC0)、pixel_font(BSD-2)、ostb 面板序列(MIT) 沿用上游 |

## ⚠️ 视频漏说的五件事

1. **Muse 本体只在美国开放**（订阅制）→ 国内刷好固件也连不上官方大脑，只能当离线玩具，或改接别的大模型。
2. **SDK token 限个人非商用**，单个 token 最多绑 **50 台**设备；把 token 编进固件卖货、公开投广告、当赠品派发都要 Meta 书面许可。**开源的是代码，不是接入权。**
3. 官方原话「built by hackers, for hackers, just for fun」，**as-is 无保修**，副作用包括刷成砖、失去保修、电压不稳。
4. 社区设备**没有厂商认证**，配对抗不住中间人攻击 —— 只能放在自己信任的网络里。
5. NVS 未加密时，**拿到板子实物的人能直接读出 Wi-Fi 密码和 token**；官方建议开启 `CONFIG_HOMEHUB_NVS_ENCRYPTION`。

## 🚀 可执行的下一步

- **只想玩本地 AI 不碰 Meta**：固件换 [`78/xiaozhi-esp32`](https://github.com/78/xiaozhi-esp32)（小智），或自己接 OpenAI / Gemini 兼容接口 —— 官方固件的 `esp32/components/minimp3` 和面板初始化代码本就参考了小智项目。
- **真要接 Muse**：需要美国区 Muse 订阅 + gadgets.muse.ai 领 token，然后 `git clone` 仓库、把 `esp32/AGENTS.md` 丢给任意 coding agent（Claude Code / Codex 都行，不锁 Muse Code）让它按板型编译烧写。
- **选板**：想要「Muse 控智能家居」的内网隧道，必须选**带 PSRAM** 的板子（ESP32-S3 带 PSRAM / ESP32-C5 DevKitC-1）；经典 ESP32 与 ESP32-C6 无 PSRAM 跑不了隧道。
- **先看再买**：`esp32/simulator/` 里有 412×412 桌面模拟器，不买硬件也能先把 UI 跑起来。

## 🏷️ 标签

#抖音采集 #ESP32 #Muse #Meta #开源硬件 #DIY #智能家居
