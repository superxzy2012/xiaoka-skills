---
title: "LoopX — 长周期AI Agent控制平面（200+小时连续任务，断电重启都能恢复）"
source: "https://v.douyin.com/jEu-zCqzelo/"
platform: douyin
type: video
author: "青青王-AI"
published: 2026-09-03
captured: 2026-09-03
tags: [AI工具, Agent, 长周期任务, LoopX, 控制平面, 自进化]
confidence: A
---

## 核心信息

- **项目名**：LoopX
- **作者**：huangruiteng（华人开发者）
- **GitHub**：[huangruiteng/loopx](https://github.com/huangruiteng/loopx)
- **Stars**：~5.5k（增长很快）
- **许可**：Apache 2.0（v0.4.8 起，之前是 MIT）
- **定位**：长周期 AI Agent 的状态控制平面（Stateful Control Plane）
- **一句话**：让 AI 盯着一个目标持续干好多天，断电重启都能恢复，目标/证据/权限/计划全存在模型外部

---

## 解决的痛点

| 现在的问题 | LoopX 的解法 |
|-----------|-------------|
| 会话一断状态全丢 | 状态存在模型外部，重启/换工具/换 Agent 都能续上 |
| 跑着跑着忘了最初目标 | 目标独立存储，每轮都对齐 |
| 大任务没拆没法验证 | 自动拆成可验证的小步骤，证据不够就继续验证 |
| 遇到问题不会调整 | 自主规划路线，需要人判断时主动停下询问 |
| 多 Agent 无法协作 | 跨 Codex/Claude Code/Cursor/dsh 共享状态 |

---

## 核心设计理念

> **Keep the loop moving. Keep the judgment human.**
> 让循环持续运转，让判断保留在人手中。

### 不是什么
- ❌ 不是又一个 Agent 框架（它跑在现有 Agent 之上）
- ❌ 不是模型替代品（它管理状态，不做推理）
- ❌ 不是任务管理器（它有证据、有门槛、有治理）

### 是什么
- ✅ **状态内核**（State Kernel）：轻量级本地优先的状态管理
- ✅ **控制平面**（Control Plane）：决定下一步做什么、要不要停、问不问人
- ✅ **治理层**（Governance）：配额、门禁、证据、人工审核
- ✅ **恢复机制**（Recovery）：断电、断网、换工具都能恢复

---

## 四大核心能力

### 1. 🔄 持久状态（Durable State）
- 目标、待办、门禁、证据、配额、交接 —— 全部存在模型外部
- Agent 只是执行有界的轮次，状态由 LoopX 保管
- 跨工具、跨会话、跨 Agent 都不丢状态

### 2. 🎯 语义决策（Semantic Decisions）
- 大任务自动拆解为可验证的小步骤
- 证据不够 → 继续验证
- 遇到问题 → 调整路线
- 需要人工判断 → 主动停下询问

### 3. 🛡️ 治理与门禁（Governance & Gates）
- **配额管理**：控制 Agent 运行次数/时间/成本
- **门禁机制**（Gates）：关键节点必须通过验证才能继续
- **保护操作**：受保护的更改需要预览 + 确认 + 凭证
- **证据回写**：每次执行的结果作为证据存入状态

### 4. 🤝 人机协作（Human-Agent Collaboration）
- 不是全自动无人值守，而是人机协作
- 需要人判断时主动停下来
- 人可以随时介入、调整目标、批准关键操作
- LoopX 状态（不是浏览器）是权威真相来源

---

## 技术架构

### 支持的 Agent Harness
- **Codex App**（主推，有 heartbeat 自动化）
- **Codex CLI**（TUI 模式）
- **Claude Code**
- **Cursor**
- **dsh**
- **自建 Agent**（通过 CLI / API 接入）

### 核心组件
```
LoopX
├── State Kernel        # 状态内核（目标/待办/证据/配额）
├── Control Plane       # 控制平面（决策下一步）
├── Governance Layer    # 治理层（门禁/配额/审核）
├── Recovery Engine     # 恢复引擎（断点续跑）
└── Integrations        # 各 Agent 集成
    ├── Codex App
    ├── Claude Code
    ├── Cursor
    └── ...
```

### 心智模型：Agent 原生看板
> 一种有用的思维模型是「Agent 原生的 Kanban」
> - 卡片承载身份、权限、证据、延续性
> - 移动通过 claim/gate/monitor/writeback 等验证操作
> - 看板是可视化表示，LoopX 状态才是真相来源

---

## 实际展示的案例

### 案例 1：开源 Issue 修复（200+ 小时）
- 公共贡献时间线，跨越 200+ 小时
- PR 交付 + 可复用的修复知识共同进化
- 从首次创建 PR 到审查/更新，完整时间线
- Issue-Fix 能力持续维护仓库上下文、知识、审查偏好

### 案例 2：自动 ML 实验（200+ 小时）
- 200+ 小时的实验时间线
- 假设、匹配证据、失效谱系、运行复现、提升/停止门禁
- 全部在一张图里可见
- 自主设计实验 → 运行 → 分析结果 → 调整假设

> 注意：200+ 小时是**自然时间**（任务持续推进的时间），不是模型连续计算了 200 小时。

---

## 安装与使用

### 安装（已验证 ✅）
```bash
pip install loopx
# 版本：0.5.4
```

### 快速开始
```bash
# 检查安装
loopx doctor

# 启动仪表盘（Web/PWA）
loopx dashboard

# 开始一个长周期目标
loopx start-goal --guided --project . --goal-text "你的目标描述"
```

### 常用命令
```bash
# 查看状态
loopx status                    # 当前目标、门禁、下一步
loopx diagnose --goal-id <ID>   # 构建精简证据包

# 待办管理
loopx todo --help               # 添加/认领/完成/更新/归档

# 配额管理
loopx quota should-run          # 判断下一轮是否该运行

# 技能安装
loopx slash-commands --install  # 刷新主机斜杠命令技能
```

### Codex 中使用
```
/loopx <目标描述>    # 开始或继续一个长周期目标
/loopx               # 让 Agent 检查 LoopX 状态
```

---

## 个人 Agent 工作空间（Personal Agent Workspace）

LoopX 提供统一的本地优先工作空间，整合：
- 🎯 Goals（目标）
- 👀 Attention（关注）
- 💬 Conversations（对话）
- ✅ Tasks（任务）
- 📁 Files（文件）
- 📅 Schedules（日程）
- 🔄 Recovery（恢复）

### 特点
- **跨 Agent 续跑**：Codex → Claude Code → 直接模型，状态不丢
- **保护操作审查**：类型化预览 + 明确确认 + 执行凭证
- **本地优先**：数据存在本地，不上传云端
- **状态权威**：LoopX 状态是唯一真相来源，不是浏览器

---

## 对 13BIT / Hermes 的价值

### 直接价值
1. **长周期任务自动化**：比如定时监控竞品、持续数据爬取、周期性报告生成
2. **跨 Agent 状态共享**：Hermes + OpenClaw + 飞书 bot 可以共享任务状态
3. **断点恢复**：Agent 崩溃/电脑重启/网络中断，回来接着干
4. **治理能力**：配额控制、门禁审核，防止 Agent 跑偏或超支
5. **证据沉淀**：每次执行都有记录，可复盘、可优化

### 与现有系统的关系
| 现有能力 | LoopX 补充 |
|---------|-----------|
| Hermes 会话式执行 | 跨会话持久状态 + 长周期治理 |
| Cron 定时任务 | 智能调度 + 证据驱动 + 自适应调整 |
| OpenClaw 多 Agent | 统一状态层 + 任务交接 |
| 技能系统 | 基于证据的技能进化（和 OpenSpace 互补） |

### 风险与注意事项
- ⚠️ 项目比较新（v0.5.x），API 可能变动
- ⚠️ 主要面向 Codex/Claude Code，Hermes 集成需要自己接
- ⚠️ 治理逻辑需要结合实际业务配置
- ⚠️ 本地存储，多设备同步需要额外方案

---

## 关键截图

| 项目主页 | 两大案例 |
|---------|---------|
| ![项目主页](../attachments/20260903-jEu-zCqzelo/f_02.png) | ![两大案例](../attachments/20260903-jEu-zCqzelo/f_05.png) |

| 个人工作空间 | Agent看板心智模型 |
|------------|----------------|
| ![工作空间](../attachments/20260903-jEu-zCqzelo/f_08.png) | ![看板模型](../attachments/20260903-jEu-zCqzelo/f_13.png) |

---

## 完整口播

> 这个开源项目能让AI盯着一个目标，持续干上好多天。哪怕任务暂停、电脑重启，它回来之后依然知道自己干到了哪一步。官方展示的两条长周期任务轨迹，都跨越了200多个小时。注意这是任务持续推进的自然时长，不是模型连续计算了200个小时。它把目标、代理、证据、权限和下一步计划，全部保存在模型外部，所以AI不再只靠聊天记录运行，也不容易跑着跑着就忘记最初的任务。更关键的是，它会把大任务拆成一个个可验证的小步骤，证据不够就继续验证，遇到问题就调整路线，需要人来判断就主动停下来询问。用它来做自动化实验、长期研究，甚至定时监控项目进度都非常合适。建议收藏，想让AI长期干活的时候，直接回来抄作业。

---

**真实性核验**：✅ 已验证
- GitHub 仓库存在：huangruiteng/loopx，~5.5k Stars，Apache 2.0
- pip 安装成功：loopx 0.5.4，CLI 功能完整
- 官方文档有中文版，飞书文档也有
- 两个 200+ 小时案例与官方描述一致
- 支持 Codex/Claude Code/Cursor/dsh 等多平台
