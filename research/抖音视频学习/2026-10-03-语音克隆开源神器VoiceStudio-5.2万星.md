---
tags: [抖音, 开源, AI语音, 语音克隆, VoiceStudio, 本地部署]
created: 2026-10-03
source: 松石AI说（抖音图文）
url: https://www.douyin.com/note/7685236741405445422
aweme_id: 7685236741405445422
repo: debpalash/VoiceStudio
verified: 2026-10-03
---

# 开源语音克隆神器 VoiceStudio（5.2 万星）

## 视频原文（松石AI说，图文帖）

> 开源语音克隆神器。卧槽，这谁干的！！？
一个人把 ElevenLabs 开源了，还让你装自己电脑上跑。
GitHub 都快 3万星了，仓库叫 VoiceStudio。
你就给它一段干净的人声，它能把这声音学下来。
视频也能配成 646 种语言。有声书、听写、转文字它也干。 引擎还不止一套，给了 14 个。ElevenLabs 自己才 32 种语言。不按字收钱，也没次数限制，音频也不上传。
有人用 5090 跑过，说还差点意思。但这个不用掏钱，声音还留在自己电脑里！还要什么自行车！ 
#ai语音克隆 #声音复刻 #语音ai #ai声音克隆 #voicestudio

## 仓库核实结果

**`debpalash/VoiceStudio`** — https://github.com/debpalash/VoiceStudio

| 项 | 值 |
|---|---|
| ★ 星数 | **52,017** |
| fork | 5,795 |
| license | **AGPL-3.0**（传染性，商用需注意）|
| 创建 | 2026-04-09 |
| 最后更新 | 2026-10-03 |
| open issues | 84 |

## 逐条核实视频说法

| 视频说法 | 核实 | 依据 |
|---|---|---|
| GitHub 快 3 万星 | ⚠️ **实际 5.2 万** | 低报 27%，视频发布后还在涨 |
| 仓库叫 VoiceStudio | ✅ | `debpalash/VoiceStudio` |
| ElevenLabs 开源替代 | ✅ | README 首句 "the open-source, fully-local ElevenLabs alternative" |
| 装自己电脑上跑 | ✅ | Electron 应用 + 本地 Python 后端，CPU 也可跑 |
| 646 种语言 | ✅ | README 提及 646 |
| 有声书/听写/转文字 | ✅ | Audiobooks / Dictation / Transcription 均为官方特性 |
| 引擎「14 个」 | ❌ **官方列 27 个** | `docs/feature-catalog.md`：语音生成 17 + ASR 10 |
| ElevenLabs 才 32 种语言 | ✅ | README 对比 |
| 不按字收钱、无次数限制 | ✅ | 本地跑，无计费 |
| 音频不上传 | ✅ | Local-first 设计 |
| 5090 跑「还差点意思」 | ⚠️ 无法核实 | 无 benchmark 数据在手 |

## 重要提醒

1. **AGPL-3.0 传染性许可** — 网络提供服务需开源，商业闭源集成前必须读 `LICENSE` 和 `docs/legal/`。
2. **模型各有独立许可** — README 原文：*"Models have their own licenses; review them before commercial use."*
3. **克隆他人声音需授权** — README 原文：*"Clone voices only with permission."*
4. **无独显也能跑**，只是慢（CPU 模式装小体积 PyTorch）。

## 中文社区分支

| 仓库 | ★ | 说明 |
|---|---|---|
| `bayshier/voicestudio-zh` | 16 | 官方认可的中文版，AGPL-3.0，2026-08-31 |

## 我能怎么用

- **有声书批量生成** — 本地跑无次数限制，比云 API 省
- **视频配音** — 抖音素材本地化配音
- **WhisperX / FunASR** — 本机已有 Whisper 依赖，可直接对接
- **MCP Server** — 官方内置 MCP，可挂进我的技能体系

## 相关技能

- `openai-whisper` — 本机已有 Whisper 转写
- `text_to_speech` — 现有 TTS 工具，可评估是否替换
- `find-skills-xiaoka` — 本条目即为「先查 GitHub」流程产物
