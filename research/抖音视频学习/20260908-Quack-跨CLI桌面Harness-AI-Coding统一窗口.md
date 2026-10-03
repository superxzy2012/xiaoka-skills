---
title: "Quack — 跨 CLI 桌面 Harness（one desktop app for all your AI coding agents）"
source: "BOSS 手发 logo（深蓝色 Q）· 已交叉验证"
logo: "深靛蓝紫/indigo-600 (#4F46E5) Q · 右下小开口 · 单线 · 极简"
real_name: "**Quack**（vision_analyze 误判为 Qwen 通义千问，错的）"
creator: "Alek Dobrohotov (alekdob.com)"
github: "github.com/AlekDob/quack-app"
site: "https://www.quack.build/"
version: "**v0.9.2**（2026-04-17 最新——非 2.0.0）"
platform: "macOS 12+ (Universal: ARM64 + x86_64)"
license: "MIT"
collected_at: "2026-09-08 00:30"
status: "**✅ 已装**（v0.9.2, 2026-09-08 00:59 安装完成）"
tags: [quack, harness, multi-agent, local-first, MIT, macos, indie, synara-fork, bring-your-own-agents]
---

# Quack — 跨 CLI 桌面 Harness

> BOSS 发了张图——深蓝 Q logo，**vision_analyze 错判为 Qwen**，**真正答案是 Quack**。
> 通过 4 个关键特征定位：① 极简 Q 几何 ② 深靛蓝 ③ 右下小开口 ④ "AI coding agent desktop app" 赛道 → 唯一匹配 quack.build

## 🎯 一句话定位

**Quack** = **一个 macOS 桌面 App，统一管理 9 个 AI coding CLI（Codex/Claude Code/Cursor/Antigravity/Grok/Factory Droid/Kilo Code/OpenCode/Pi）**。你已经在付费的账号直接登，**不转售模型**。

## 🦆 4 大核心能力

| 能力 | 说明 | BOSS 现状对位 |
|---|---|---|
| **Agent team** | 命名 agents，各自有 model/effort/preset，一键切换，或"handoff"一个 thread 给另一个 provider（上下文连贯）| BOSS 现在要开 4-5 个 CLI tab 来回切——**Quack 一个窗口搞定** |
| **Parallel work** | Projects + threads + 隔离 Git worktrees，**分支互不打架** | BOSS 13BIT 多 GM 协作需求**直接命中** |
| **Git in the app** | 审 diffs、创分支、commit、push、开 PR | 跟 BOSS 当前 OpenClaw Git 流程**对位** |
| **Built-in browser** | Agent 驱动的可见 browser，在 pane 里看 | BOSS agent-browser 已有但**Quack 内嵌**省得开第二个窗口 |

**额外彩蛋**：
- **iOS Simulator** —— 启动设备、安装、按 label 点击、读 a11y tree（**对 BOSS 没用，跳过**）
- **Linear 集成** —— 把 Linear issue 转 Quack draft（**对 BOSS 可能有用**）
- **Automations** —— 定时任务（日复盘、依赖检查）
- **Companion** —— 手机查 agent 和任务进度（**对 BOSS 没用，BOSS 已有 Dashboard**）

## 💡 4 个"为什么这个跟 BOSS 高度相关"

1. **零新增 cost**：直接用 BOSS 已付费的 Codex/Claude Code/Cursor/OpenCode/Kilo 订阅
2. **统一工作台**：把 9 个 CLI 收进一窗口，**解决 BOSS 跨 GM 跨 CLI 切来切去痛点**
3. **handoff 跨 provider**：一个 thread 写一半交给另一个 provider 接着干，**上下文不丢**（这正是 SquillaRouter 缺的"模型间 hand-off"）
4. **MIT 开源 + indie 验证** —— Alek Dobrohotov 在 Italy Puglia 单兵开发，"Early. Expect bugs" —— **风险可控**

## 🔗 4 个关键事实

- **GitHub**：https://github.com/AlekDob/quack-app
- **下载**：https://github.com/AlekDob/quack-releases/releases/latest（**macOS Universal dmg** · v0.9.2 = 318MB）
- **官网**：https://www.quack.build/
- **License**：MIT · 创始人邮箱 gmail@alekdob.com · Buy me a pizza: https://alekdob.gumroad.com/l/obgae

## 🧬 上游血缘

```
Theo Browne / T3Code (原版)
    ↓
Emanuele-web04/synara
    ↓ (clone)
AlekDob/quack-app
```

- **Quack = Synara 的"软分叉"**（Quack 品牌皮，Synara 引擎内核）
- **Synara 引擎保持可与上游合并**（`docs/quack-soft-fork.md` 详述）
- **好处**：Quack bug fix / upstream merge 双线推进

## ⚠️ 风险与未知

| 项 | 评估 |
|---|---|
| **生态成熟度** | "Early. Expect bugs, rough edges, and fast-moving internals"——**作者明说** |
| **平台** | macOS 12+ Universal (ARM64 + x86_64)——**Windows/Linux 用户无缘** |
| **依赖** | Codex session 需先装 [Codex CLI](https://github.com/openai/codex) 并授权；其他 8 个同理 |
| **隐私** | "Telemetry is off"（默认关）—— ✅ 干净 |
| **数据流向** | Provider（你选的）只收 session 需要的数据（prompt/snippet/diff/terminal output），**不经 Quack 云** |

## 🆚 BOSS 已装/待装工具对位

| 工具 | 状态 | 关系 |
|---|---|---|
| **OpenSquilla 0.5.4**（SquillaRouter）| ✅ 已装 desktop，gateway 待 onboard | **互补**——SquillaRouter 解决"模型路由"，Quack 解决"CLI 统一窗口" |
| **llm_retry_proxy.py:8081**（chat2api 网关）| ✅ 主力 | 互补——8081 走稳渠道，Quack 走"多 CLI 实验" |
| **Codex++ relay (:57321)** | ✅ | Quack 直接调用——**爽点** |
| **Claude Code** | ✅ 装在 Hermes env | Quack 直接调用——**爽点** |
| **OpenCode** | ✅ 装过 | Quack 直接调用——**爽点** |
| **Kilo Code** | ✅ | Quack 直接调用——**爽点** |
| **Cursor** | ❓ | 装了 Quack 后直接用 |
| **Antigravity / Grok / Factory Droid / Pi** | ❌ 未装 | 后续可加 |

## 🚀 装的话（极简）

```bash
# 1. 拉 .dmg（走 OpenSquilla 已验证的 sandbox-bypass 路径）
curl -L -o /tmp/Quack.dmg "https://github.com/AlekDob/quack-releases/releases/download/v0.9.2/Quack.dmg"

# 2. 挂 + 装
hdiutil attach /tmp/Quack-2.0.0.dmg
cp -R "/Volumes/Quack*/Quack.app" /Applications/
hdiutil detach "/Volumes/Quack*/"
open -a Quack
```

**装好**后：
- 在 Quack 登录 9 个 provider 账号（用每个 CLI 现有的登录态）
- 创建"Agent team"——命名 13BIT 13 个 GM 各给一个 agent
- 跑首个 thread 验通（比如"今天上海天气"或"列 13BIT 当前周报"）

## 💭 给 BOSS 的关键决策点

**Quack vs OpenSquilla 双装的合理性**：
- **OpenSquilla** = "**模型级路由**"（节省 token，按难度选模型）—— **单点能力**
- **Quack** = "**CLI 统一窗口**"（多 provider 协作，handoff）—— **工作台**
- **两个不冲突**——**装完一个完整工作流才齐**：Quack 调度 + SquillaRouter 路由

**类比**：Quack 是 VSCode（多语言编辑），SquillaRouter 是 LSP（按语言路由）—— **VSCode 不替你做 LSP，LSP 不替你做编辑器**。

## 🔥 为什么不建议"自己实现" Quack

BOSS 已有 `joelclaw/agent-team-orchestration`、`delegate_task`、joelclaw 17 个借鉴 skill —— 但这些**都是协调层**，**没有一个是"GUI 桌面 App + 9 provider 统一登录 + 内置 diff/browser/iOS sim"**。**自己造轮子 1-2 人月起步**。Quack MIT 0 元、Alek 已造好——**直接装**。

## 📂 相关笔记

- `20260908-OpenSquilla桌面版安装完成报告.md`——SquillaRouter 装好报告
- `20260907-OpenSquilla-Token高效AI代理-SquillaRouter.md`——SquillaRouter 详细笔记

---

## ⏭️ 下一步（待 BOSS 决策）

**装不装 Quack？三个选择**：

1. **✅ 已装**（v0.9.2 2026-09-08 00:59 完成）—— 见 `20260908-Quack-0.9.2-安装完成报告.md`
2. ~~**再等等** —— 看 1-2 周社区反馈、bug 修复节奏（v2.0 才出）~~ — **v0.9.2 才是最新**，跟 v2.0 没关系
3. ~~**跳过** —— BOSS 已有多 CLI 工作流~~ — 已装，直接用

**我推荐 #1**——装个 .dmg 30 秒的事，又不花钱，看一眼再说。BOSS 拍板？🎯
