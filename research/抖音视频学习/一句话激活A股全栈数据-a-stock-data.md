---
title: 开源项目推荐：一句话激活A股全栈数据 a-stock-data
source: douyin
author: AI探长
video_id: "7690560093624098789"
url: https://www.douyin.com/video/7690560093624098789
duration: 1m33s
date: 2026-09-30
tags: [抖音, A股, 量化, 财经数据, a-stock-data, GitHub, Skill, Claude-Code, 开源]
confidence: A
---

# 一句话激活 A股全栈数据：a-stock-data

## 项目信息（已核验）
- **仓库**：https://github.com/simonlin1212/a-stock-data
- **作者**：simonlin1212
- **Stars**：10,447（截至 2026-09-30，当日仍有更新）
- **协议**：Apache-2.0 | **语言**：Python 3.9+
- **规格**：**15 层架构 · 87 个端点 · 34 个数据源 · 零鉴权（仅 iwencai 除外）**
- **形态**：一个自包含的 `SKILL.md`（425KB，结构化 Markdown + 内嵌 Python），兼容 Claude Code / Codex / OpenClaw

## 三大亮点
| 亮点 | 说明 |
|---|---|
| 覆盖面 | 行情K线、当日逐笔、研报、信号、资金面、新闻、财务、公告、打板、ETF期权、舆情互动、宏观利率、期货大宗、事件驱动、可转债 共15类 |
| 零鉴权 | 不用自己对接接口、处理反爬，也不用花几万买专业数据；主源被封自动降级备用源 |
| Skill 分发 | 一个 skill.md 收进 Claude Code/Codex/OpenClaw 即可直接调用，从提问到数据无需写调用代码 |

## 上手指三步
1. **放 SKILL.md**：curl 把单文件拉到 Claude Code 的 skills 目录
2. **装依赖**：`pip install mootdx requests pandas stockstats numpy baostock xlrd openpyxl`
3. **对话激活**：启动后说一句「帮我看看 688017 的估值」即自动取数

Codex/OpenClaw 用户：把 SKILL.md 内容贴进系统 prompt 或项目上下文，内嵌 Python 可直接执行。

## 架构要点（视频所述）
- **行情层**：腾讯 K 线（日/周/月、前后复权、分钟级）→ 通达信盘后包（全市场日线+成交额）→ 腾讯逐笔（约3秒一笔，收盘后用成交额核对完整性）；V3.10 后 mootdx 降级留档（通达信公开服务器命令失效 #52）
- **研报层**：东财取个股研报/评级，同花顺取一致预期，爱问财做自然语言检索
- **信号/资金层**：同花顺当日强势股与题材归因、北向资金、东财板块归属、分钟级资金流向、龙虎榜席位、限售解禁日历

## 本机落地（已实测）
- ✅ SKILL.md 已封装：`~/.claude/skills/a-stock-data/SKILL.md`（425,008 字节）
- ✅ 依赖已装并全部可导入（mootdx/requests/pandas/stockstats/numpy/baostock/xlrd/openpyxl）
- ✅ **取数实测**：baostock 拉取 sh.688017 成功 — 2026-09-29 收盘 275.60，PE-TTM 358.19

## 截帧
![项目概要](../attachments/20260930-7690560093624098789/f_01.png)
![三步上手](../attachments/20260930-7690560093624098789/f_05.png)

## 完整口播转写
??? quote "Whisper 转写（small/zh，1m33s）"
    今天给大家介绍一个 A股全栈数据工具包。做量化交易开发、想用 AI 分析大 A 投资、做财经数据产品的朋友，建议先点赞收藏。

    这个项目的第一个亮点是覆盖面：行情K线、当日逐笔、研报、信号、资金面、新闻、财务、公告、打板、ETF期权、舆情互动、宏观利率、期货大宗、事件驱动、可转债，一共 15 类。第二个亮点是零鉴权，从此不用再自己对接各种接口、处理反爬，或者花几万块买专业数据。第三个亮点是分发形态，stock data 把这些收进一个 skill，Claude Code、Codex 能直接调。

    它的使用路径可以拆成三步：第一步，把 SKILL.md 下载到 Claude Code 的 skills 目录，一条 curl 命令就位；第二步，安装依赖包；第三步，启动 Claude Code 说一句话，比如「帮我看看 688017 的估值」，自动就会取数。完成这三步，你就从提问抵达了数据。

    架构文档给出 15 层结构，取舍写得很明确：东财只用于独有数据，并且内置限流。行情层里，腾讯 K 线覆盖日周月前后复权与分钟级，通达信盘后包提供全市场日线和成交额，腾讯逐笔成交约 3 秒一笔，收盘后还会用当日成交额核对完整性。研报层可以从东财取个股研报与评级，从同花顺取一致预期，还可以用爱问财做自然语言检索。信号层能看到同花顺当日强势股与题材归因、看北向资金、东财板块归属、分钟级资金流向、龙虎榜席位和限售解禁日历。从行情到研报再到资金与信号，它覆盖的是研究链条上的多个环节。

    想用起来只需要三步：下载 SKILL.md 到 Claude Code skills 目录、安装依赖、启动 Claude Code。如果你是 Codex 或 OpenClaw 用户，把 SKILL.md 的内容贴进系统 prompt 或项目上下文，内嵌的 Python 代码可以直接执行。从提问到数据，中间不再需要写调用代码。
