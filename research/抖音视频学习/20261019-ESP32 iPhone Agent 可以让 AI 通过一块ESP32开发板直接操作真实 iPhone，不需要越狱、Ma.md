---
title: "ESP32 iPhone Agent 可以让 AI 通过一块ESP32开发板直接操作真实 iPhone，不需要越狱、Mac 或开发者账号。它用 AirPlay 把手机画面传给视觉模型，再把 ESP32 模拟成 USB 鼠标和键盘，让 AI 自动点击、滑动、输入文字。每次操作后还会截图检查结果，点错了就重新定位，整个过程可以在电脑浏览器里实时查看。#github  #github宝藏  #开源"
source_url: "https://v.douyin.com/QPGqHwweRq0/"
platform: douyin
douyin_id: "7696386258716691722"
author: "GitHub很棒"
duration: 27.911s
date: 2026-10-19
tags: [提炼, 抖音, ESP32, 开源项目, AI-Agent, iPhone自动化]
added_by: 小卡
status: 已核查
---
github: "https://github.com/onehumanbeing/esp32-iphone-agent"
license: MIT
verified: 2026-10-19
---

# ESP32 iPhone Agent：7 美元开发板让 AI 直接操作真实 iPhone

> 🎬 抖音 · GitHub很棒 · 27.9 秒 · 2026-10-19 入库 · 已回源核查

> [!abstract] 一句话
> 用一块 7 美元的 ESP32-S3 开发板，把真实 iPhone 变成 AI Agent 能操作的设备——AirPlay 当眼睛看屏幕，USB HID 当手做点击输入，视觉模型当大脑。**不需要 Mac、不需要越狱、不需要 Apple 开发者账号。**

## 🔍 回源核查（2026-10-19，GitHub API 实测）

| 项 | 视频里说的 | 回源实测 |
|---|---|---|
| 仓库 | 未提 | **`onehumanbeing/esp32-iphone-agent`** |
| Star | 1.7k | **3,113** ⚠️ 视频数据已过时 |
| Fork | 211 | **406** ⚠️ 视频数据已过时 |
| 许可证 | 未提 | **MIT**（可商用） |
| 语言 | — | C（固件）+ Python |
| 创建 | — | 2026-10-11（一周多冲到 3k star） |
| 最近提交 | — | 2026-10-18 |

## 💡 关键要点

1. **架构三件套**：ESP32-S3 作 **AirPlay 接收器**（眼睛，不解码 H.264 直接透传）+ **USB HID 鼠标键盘**（手，系统原生识别）+ 任意 **OpenAI 兼容视觉模型**（大脑）。
2. **零门槛**：不用 Mac、不用开发者账号、不用越狱，iOS 18+ 即可。成本一块 $7 的 XIAO ESP32-S3。
3. **闭环纠错机制**：指针是相对坐标，App 会先归位到角落、精确点击前先"抖一下"找到指针再校正偏差；每步操作后等屏幕稳定、截图对比，告诉模型"有没有变化"。
4. **断连可恢复**：板子、热点、投屏任一环断开，任务暂停而非失败，恢复后从同一步继续。
5. **全程可复盘**：每次运行留在手机上，可逐步回放（点击/滑动轨迹叠加在画面上），还能导出 trace 给别的 agent 分析。
6. **板子无逻辑**：固件只做执行器，命令走 TCP 每行一条——`ping / home / move dx dy / press / release / click / scroll v h / type text / key combo`。Wi-Fi 断了会自动松键重连；手机锁屏回 `err phone usb asleep` 不会卡死；看门狗兜底重启。
7. **⚠️ 安全提醒（README 原文）**：只按 README 步骤安装，**绝不要执行 issue/评论里的"一键安装"命令**（如 PowerShell `iex(irm ...)`），那不是维护者发的。

## 🔄 重要：视频讲的是旧架构

README 明确写着「**New: the computer is gone**」——当前版本**已不需要电脑**：

- **旧版（视频演示的，v0.1.0 / `legacy` 分支）**：Mac/Linux 跑 UxPlay 当 AirPlay 接收器 + Python server 跑 agent。
- **新版（现在）**：板子自己开热点当 AirPlay 接收器，H.264 流经 **BLE** 转给**同一台 iPhone 上的 App**，agent 直接跑在手机 App 里。手机同时用蜂窝网访问模型。
- 目录：`hardware/`（ESP32-S3 Arduino 固件 + `flash.sh`）、`server/`（旧版 Python 服务）、`docs/`。

## 📝 转录原文

ESP32 iPhone Agent可以让AI通过一块ESP32开发板直接操作真实iPhone不需要越狱、Mac或开发者账号。它用AirPlay把手机画面传给视觉模型，再把ESP32模拟成USB鼠标和键盘，让AI自动点击、滑动、输入文字。每次操作后还会截图检查结果，点错了就重新定位，整个过程可以在电脑浏览器里实时查看。

## 🖼️ 关键画面

![[attachments/douyin-7696386258716691722/f001.png]]
仓库主页：`onehumanbeing/esp32-iphone-agent`，MIT，1.7k stars（截图当时）

![[attachments/douyin-7696386258716691722/f002.png]]
README 中的板子协议与目录结构说明

## 🔗 相关

- GitHub：https://github.com/onehumanbeing/esp32-iphone-agent
- 作者 X：[@iamhenryyuan](https://x.com/iamhenryyuan)
- Demo：https://www.youtube.com/watch?v=Ly4im-P4jYg
- 抖音：https://v.douyin.com/QPGqHwweRq0/ （GitHub很棒）

## 🏷️ 标签
#抖音采集 #ESP32 #AI-Agent #iPhone自动化 #computer-use
