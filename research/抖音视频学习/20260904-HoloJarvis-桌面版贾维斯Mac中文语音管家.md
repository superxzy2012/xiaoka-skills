---
title: HoloJarvis - 桌面版贾维斯，Mac中文语音管家
source: https://v.douyin.com/VYdcloNp0QU/
type: 抖音视频
author: 树
duration: 约27秒
stars: 未知
tags: [抖音, 语音助手, 贾维斯, HoloJarvis, 开源, 桌宠, 本地AI, Whisper]
created: 2026-09-04
confidence: A
---

# HoloJarvis - 桌面版贾维斯，Mac中文语音管家

> 来源：抖音 @树 | 开源免费
> 视频时长：约 27 秒 | 转写约 130 字

---

## 🎯 核心价值

**一句话**：给电脑装一个「贾维斯」——喊一声就办事，钢铁侠风格全息桌宠 + 本地语音识别 + 任意大模型 + 工具调用。

| 特性 | 说明 |
|------|------|
| 唤醒词 | 「贾维斯」（中文语音唤醒） |
| 语音识别 | 本地 Whisper，不上传，免费 |
| 大模型 | 随便接（中转站/DeepSeek/GPT 等 OpenAI 兼容格式） |
| 工具调用 | 开软件、查天气、发微信、整理文件 |
| 语音合成 | 系统TTS + 可选克隆音（GPT-SoVITS） |
| 桌宠 | 钢铁侠全息风格青色面板 |
| 平台 | macOS + Windows |
| 协议 | 开源免费 |

---

## 🔧 技术架构

```
语音输入 → Whisper本地识别 → 大模型(可配置) → 工具调用/MCP → GPT-SoVITS(可选)
                ↓                                                ↑
         文字转文字思考                                    克隆音回复
```

**关键设计：**
- **全本地语音**：Whisper 本地跑，隐私安全
- **模型无关**：OpenAI 兼容接口，随便换模型
- **MCP 支持**：可扩展工具能力
- **配置极简**：几个 txt 文件搞定，不用改代码

---

## 🚀 快速开始（macOS）

```bash
git clone https://github.com/wqq64842-commits/holojarvis.git
cd holojarvis

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置（复制示例文件后填自己的）
cp base_url.txt.example base_url.txt   # 中转站地址，如 http://127.0.0.1:8081/v1
cp api_key.txt.example  api_key.txt    # API Key
cp model.txt.example    model.txt      # 模型名，如 deepseek-chat

# 启动（带桌宠）
./run.sh
```

启动后喊一声「贾维斯」或点一下桌宠反应堆，就能对话。

---

## 💡 亮点功能

1. **钢铁侠风格桌宠**：桌面悬浮全息面板，颜值党狂喜
2. **本地语音识别**：Whisper 跑本地，零延迟、零泄露
3. **克隆音回复**：接入 GPT-SoVITS，用自己的声音回复
4. **微信自动化**：通过界面自动化发微信（依赖已登录的微信客户端）
5. **MCP 工具生态**：支持 MCP 协议，工具可无限扩展
6. **零配置可用**：系统 TTS 直接用，克隆音是可选增强

---

## 📌 对 BOSS 的价值

- **语音交互入口**：和现有 8081 网关完美兼容，把 HoloJarvis 接到 chat2api-tool 上就能用
- **桌面端语音助手**：比打字快，适合快速查东西、开应用
- **开源可改**：可以自己加技能、接 MCP 工具，和 Hermes 技能联动
- **桌宠颜值**：青色全息面板，做演示/录屏效果好

---

## 📹 视频关键帧

| 帧 1 | 帧 2 | 帧 3 |
|------|------|------|
| ![f_02.png](/attachments/20260904-VYdcloNp0QU/f_02.png) | ![f_05.png](/attachments/20260904-VYdcloNp0QU/f_05.png) | ![f_08.png](/attachments/20260904-VYdcloNp0QU/f_08.png) |

---

<details>
<summary>📝 完整口播转写（点击展开）</summary>

Siri 弱爆了，我直接给电脑造了个贾维斯，还不要钱
喊一声他就醒，开软件、查天气、发微信、整理文件，动口不动手
声音本地识别不上传，大模型随便接
还能用自己克隆的声音回话
桌面那块青色全息面板，钢铁侠看了都眼馋
开源免费，GitHub HoloJarvis，搜了就能装

</details>

---

**入库时间**：2026-09-04 | **入库人**：小豆
