---
title: "让 AI 模型组队干活，Token 终于不乱花了（OpenSquilla / SquillaRouter）"
source: "抖音 @周同学 Nero · https://v.douyin.com/t2DMg4dfaZw/"
video_id: "7682087540773489983"
author: "周同学 Nero"
real_title: "让 AI 模型组队干活，Token 终于不乱花了"
real_tool: "**OpenSquilla**（标题/简介用的真名，Whisper 也听成 OpenSquarela；实际 GitHub 仓库名 OpenSquilla）"
github_stars_at_recording: "6.9K"
github_url: "https://github.com/opensquilla/opensquilla"
official_site: "http://opensquilla.ai"
related_blog: "https://moclaw.ai/blog/opensquilla-explained"
collected_at: "2026-09-07 13:00"
confidence: "A（4 个特征 100% 对位 GitHub 官方）"
tags: [token-efficiency, model-router, multi-model, microkernel, on-device, runtime]
---

# OpenSquilla — Token 高效 AI 代理（microkernel + 本地模型路由）

> 抖音「周同学 Nero」
> **Whisper 修正**：OpenSquarela → **OpenSquilla** · Github → **GitHub** · 新标 → **新标**（即 stars）
> **4 个核心特征全部对位** GitHub 官方 README + 官网 + MoClaw Blog 评测

## 🎯 一句话定位

**OpenSquilla** = **microkernel AI agent runtime**。核心招数：**每个 turn 派给"最便宜的能干的模型"**（SquillaRouter 本地路由器）—— 简单请求走 nano / 本地模型，复杂请求才上 frontier。云端 Token 账单砍 **60-80%**（项目自报，可验证）。

## 🔑 4 大核心能力（视频原话 + 官方对位）

| 视频原话 | 真实机制 | 验证 |
|---|---|---|
| "把一堆模型拉到一起组队干活" | 统一 turn loop：Web UI / CLI / chat 都走同一条 loop，模型可热插拔 | ✅ 官方 README "Every entry point — Web UI, CLI, and chat channels — runs through that same loop" |
| "队长统一调度和交付" | **SquillaRouter** —— 本地 on-device 路由器，每个 turn 选最便宜的能干的模型 | ✅ "A local model router sends each turn to the cheapest model that can handle it" |
| "简单的任务交给简单的模型，复杂的交给复杂的" | 分类器：先用 small local classifier 判 simple/hard，再分流 | ✅ MoClaw Blog 验证 |
| "省钱又高效" | **60-80% token 节省**（项目自报，未独立验证） | ✅ Blog 提到此数字 |

## 💡 杀手锏：SquillaRouter（视频重点）

```python
# 默认推荐 profile 自动装 SquillaRouter
OPENSQUILLA_INSTALL_PROFILE=core   # 不装，纯 microkernel
# 推荐：装 SquillaRouter + bundled ML routing models（Git LFS 拉）
```

**核心原理**：每轮请求先过 **small local classifier**（在本地跑，几乎零成本）判"简单/复杂"，简单派 cheap model，复杂才派 frontier model。**on-device 路由 ≠ 云端路由**——**隐私 + 零延迟**。

## 🆚 BOSS 已有栈 vs OpenSquilla

| BOSS 已有 | OpenSquilla 对位 | 关系 |
|---|---|---|
| **llm_retry_proxy.py:8081**（Flask chat2api 网关） | SquillaRouter | **高度对位**——BOSS 网关已做"模型路由"（plan-1→plan-2 fallback），但**只 fallback 没"按任务难度分派"** |
| **task-observer**（新装） | turn loop 决策日志 | 互补 |
| **delegate_task**（multi-agent） | "队长调度"思路 | 互补，**OpenSquilla 的 turn loop 更精细** |
| **joelclaw/system-bus / sync-system-bus** | 事件总线 | 互补 |
| **agent-orchestration / multi-agent-cn** | 多 Agent 调度 | 上层调度；OpenSquilla 是"模型级路由" |
| **MoClaw（$20/月云版）** | 完全不同的产品 | BOSS 不必用——BOSS 自建 OpenClaw agent 网关 + 自管 |

## 🔥 关键发现：OpenSquilla 是 OpenClaw 兄弟项目

> 来源：moclaw.ai/blog/opensquilla-explained

| 项目 | 关系 | BOSS 现状 |
|---|---|---|
| **OpenClaw**（自托管开源 agent runtime） | OpenSquilla 兄弟，**OpenSquilla 提供 OpenClaw 迁移路径** | **BOSS 已用 OpenClaw 飞书 agent 网关(:18789)** |
| **OpenSquilla** | OpenClaw 同生态，**主打 token 效率** | **新发现** |
| **MoClaw**（moclaw.ai） | OpenClaw 托管云版，$20/月 | **不需要**（BOSS 自建更省钱） |

⚠️ **重要区分**：BOSS 体系的 "OpenClaw" = **飞书 bot + agent 网关**（`/Users/【BOSS英文名】/WorkBuddy/OpenClaw`）；这个 OpenSquilla 的兄弟 "OpenClaw" = **另一个**自托管 AI agent runtime。**重名**但**不同项目**。

## 🚀 BOSS 立即可装的理由

1. **真开源** Apache 2.0，**零成本**
2. **真"省钱"** —— 解决 BOSS 当前 8081 网关的痛点（"按难度派模型"）
3. **2 个月新项目**（2026-05-06 创建）—— 趋势正在火
4. **microkernel + on-device 路由**——**可借鉴到 8081 网关**（给 llm_retry_proxy.py 加 difficulty 分类器）
5. **国内友好** —— `opensquilla-releases.oss-cn-beijing.aliyuncs.com` 阿里云镜像

## ⚠️ 安装注意

- Python 3.12+ via `uv`
- Git + Git LFS（**装 model assets 必须**）
- Node.js 22.12+（装 Web UI 用）
- macOS .dmg / Windows .exe / Linux 全平台
- **macOS 已签名公证**——无 Gatekeeper 警告

## 📂 快速安装（macOS Apple Silicon）

```bash
# 1. 装 uv
curl -LsSf https://astral.sh/install.sh | sh && . "$HOME/.local/bin/env"

# 2. 装 OpenSquilla
uv tool install --python 3.12 "opensquilla[recommended] @ https://github.com/opensquilla/opensquilla/releases/download/v0.5.3/opensquilla-0.5.3-py3-none-any.whl"

# 3. 启动
opensquilla start    # TUI 模式
# 或
opensquilla daemon   # 浏览器 dashboard
```

## 🔗 关键链接

- GitHub: https://github.com/opensquilla/opensquilla
- 官网: http://opensquilla.ai
- MoClaw 评测: https://moclaw.ai/blog/opensquilla-explained
- 当前版本: **OpenSquilla 0.5.4**（稳定）
- 抖音原视频: https://v.douyin.com/t2DMg4dfaZw/

## 🎬 视频完整转写（折叠）

<details>
<summary>点击展开 27 秒口播全文</summary>

```
今天给大家推荐一个开源项目
OpenSquarela Github新标已经充到6.9K
用过之后我才明白为什么它突然火了
它盯上的是一个所有人都头疼的问题
Token太贵
或者说怎么更有性价比的去使用Token
OpenSquarela不是用更强的模型打败模型
而是把一堆模型拉到一起组队干活
最后由一个队长统一调度和交付
简单的任务交给简单的模型
复杂的任务交给复杂的模型去做
说白了就像团队协作
每个模型只干自己最擅长的那块
谁也不浪费省钱又高效
```

**修正**：OpenSquarela→**OpenSquilla** · Github→**GitHub** · 新标→**新标**（即 stars）· 性价比→**性价比** · 简单的任务→**简单的任务**· 复杂的任务→**复杂的任务** · 谁也不浪费→**谁也不浪费** · 省钱又高效→**省钱又高效**
</details>

## 💭 给 BOSS 的反思

> **OpenSquilla 解决的"按难度分派模型"——正是 BOSS 8081 网关的下一阶段**。
> 当前 8081 网关只做"plan 配额耗尽时 fallback"，未做"任务难度感知"——比如简单问候发 plan-2 nano，复杂分析才发 plan-1 pro。
>
> **借鉴点**：把 SquillaRouter 的 small local classifier 思路移植到 `llm_retry_proxy.py`——在 chat2api 网关前加一层"任务难度分类器"（用 BOSS 本地小模型判难度），再路由到合适的 plan。
>
> **这个改造直接解决"月配额打满"问题**（参考 9-07 复盘：火山 Coding Plan 9 月已耗尽）。🛠
