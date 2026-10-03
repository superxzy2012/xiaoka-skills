---
title: "mattpocock/skills — 真正工程师的 AI 编程技能包（24.5万星，20+可组合技能）"
source: "https://v.douyin.com/WtA7IrP0D40/"
platform: douyin
type: video
author: "鼠鼠不加班"
published: 2026-09-03
captured: 2026-09-03
tags: [douyin, mattpocock, AI编程, 工程规范, TDD, 代码审查, 技能包]
confidence: A
related: [[Karpathy编码四原则]]
---

## 来源

- 抖音链接：https://v.douyin.com/WtA7IrP0D40/
- 作者：鼠鼠不加班
- 形式：视频（约 40 秒）
- 项目：mattpocock/skills
- GitHub：https://github.com/mattpocock/skills

---

## 是什么

**mattpocock/skills** 是知名 TypeScript 工程师 **Matt Pocock**（Node.js 早期核心开发者）出品的 AI 编程技能包。

> 「这是真正的工程师技能项目」—— 项目 README 第一句话

- ⭐ **~24.5 万 Star**（视频里说的 129K 是旧数据，现已翻倍）
- 📦 **20+ 可组合技能**，分工程类和生产力类
- 🧩 小而可组合、模型无关、基于真实工程经验（不是 vibe coding）
- 🎯 核心理念：**用技术规范强行约束 AI 行为**，让 AI 不再凭感觉写代码

---

## 技能全景

### 🛠️ 工程类（Engineering）

| 技能 | 用途 | 一句话总结 |
|------|------|-----------|
| **diagnosing-bugs** | 诊断硬 bug / 性能回归 | 有纪律的诊断循环：重现→最小化→假设→工具→修复→回归测试 |
| **code-review** | 代码审查 | 双轴审查（标准 + 规格），并行子代理互不污染 |
| **tdd** | 测试驱动开发 | RED→GREEN 循环，测试只在接缝处测行为不测实现 |
| **domain-modeling** | 领域建模 | 主动打磨领域模型，CONTEXT.md + ADR 文档体系 |
| **triage** | 问题分诊 | 状态机驱动的 bug/enhancement 分类，产出 agent-ready brief |
| **to-spec** | 需求转规格 | 把模糊需求转成可执行的规格说明 |
| **to-tickets** | 规格拆工单 | 把规格拆成可执行的工单 |
| **implement** | 实现 | 按规格实现功能 |
| **prototype** | 原型验证 | 快速验证想法，不追求质量 |
| **wayfinder** | 代码库导航 | 快速理解陌生代码库结构 |
| **codebase-design** | 代码库设计 | Design it twice 方法论 |
| **improve-codebase-architecture** | 架构改进 | 系统性改进代码库架构 |
| **research** | 技术调研 | 结构化技术调研方法 |
| **grill-with-docs** | 文档质询 | 用文档反向质询设计 |
| **resolving-merge-conflicts** | 解决合并冲突 | 结构化解决 merge conflict |
| **wizard** | 向导模式 | 交互式引导用户做决策 |
| **ask-matt** | 问 Matt | 模拟 Matt 的思维方式回答问题 |

### ⚡ 生产力类（Productivity）

| 技能 | 用途 |
|------|------|
| **grill-me** | 深度拷问你的想法 |
| **grilling** | 拷问方法论文档 |
| **wait-what** | 歧义澄清 |
| **handoff** | 任务交接 |
| **writing-for-agents** | 给 AI 写说明的技巧 |
| **teach** | 教学技能 |
| **to-questionnaire** | 需求转问卷 |

---

## 🌟 核心精华（直接可用）

### 1. 诊断 Bug 六步法（diagnosing-bugs）

> **核心信条：先建反馈循环，再找 bug。** 没有 tight 的 pass/fail 信号，盯着代码看没用。

```
Phase 1: 建立反馈循环 ← 最重要的一步
  ├─ 失败测试（unit/integration/e2e）
  ├─ curl / HTTP 脚本
  └─ CLI 调用

Phase 2: 复现并最小化
  └─ 缩小到最小复现条件

Phase 3: 提出假设
  └─ 基于证据，不是凭感觉

Phase 4: 用工具验证
  └─ debugger / profiler / log

Phase 5: 修复
  └─ 最小改动修复

Phase 6: 回归测试
  └─ 确保修复不引入新问题
```

### 2. TDD 核心原则

- **测试测行为，不测实现** — 代码可以重构，测试不该变
- **只在接缝（seam）处测试** — 公共接口，不是内部函数
- **好测试读起来像规格说明** — "用户能用有效购物车结账" > "checkout 返回 true"
- 每个 RED→GREEN 循环都要遵守：先写失败测试 → 最小实现让它过 → 重构

### 3. 代码审查双轴法

| 轴 | 检查什么 |
|----|---------|
| **Standards（标准）** | 代码是否符合项目的编码规范？ |
| **Spec（规格）** | 代码是否忠实实现了原始需求/规格？ |

> 双轴并行做，互不污染上下文

### 4. 领域建模三件套

1. **CONTEXT.md** — 项目领域词汇表 + 核心概念
2. **ADR（Architecture Decision Record）** — 架构决策记录
3. **CONTEXT-MAP.md** — 多领域上下文地图（大项目用）

> 边做边写，不是事后补。术语一固化就写下来。

---

## vs Karpathy 编码四原则

| 来源 | 侧重点 | 风格 |
|------|--------|------|
| **Karpathy** | 极简、少写、先想 | 哲学层面，4 条铁律 |
| **mattpocock/skills** | 工程流程、可操作步骤 | 方法论文档，20+ 可组合技能 |

> 两者互补：Karpathy 是战略（写不写、写多少），mattpocock 是战术（怎么写、按什么流程写）。

---

## 🎯 对 13BIT 的落地价值

1. **diagnosing-bugs** 最实用 — 我们天天排查问题，这套循环可以直接套用
2. **code-review 双轴法** — agent 写的代码可以按这个标准自查
3. **domain-modeling** — 可以用来规范我们技能库的命名和术语
4. **triage 分诊** — 对 13BIT 多 agent 协作有参考价值

> 已封装 `diagnosing-bugs` 为本地 Hermes 技能，遇到 bug 诊断场景自动触发。

---

## 关键帧

![首页介绍](attachments/20260903-WtA7IrP0D40/key_1.png)
![GitHub页面](attachments/20260903-WtA7IrP0D40/key_2.png)
![技能列表](attachments/20260903-WtA7IrP0D40/key_3.png)
![诊断循环](attachments/20260903-WtA7IrP0D40/key_4.png)

---

## 口播全文

<details>
<summary>点击展开完整口播（261 字）</summary>

```
为了借AI瞎写代码的臭毛病
一个大弦程序员直接下场正面出手
这个项目在GitHub上已经狂揽129K的Star
开头第一句话就很硬
这是真正的工程师技能项目
作者是著名程序员Mike Pocac
Chenversial工程师参与过Node.js早期开发
别看整个项目只有七十行代码
理念全是农所版的AI编程原则
他做的是很直接
用一套技术规范
强行约束AI的行为
专门解决大模型听不懂话
回答啰嗦
浪费Token
代码太优种的问题
以前AI是想到哪写到哪
现在是必须按规矩写
让AI不再凭感觉编程
而是按工程标准输出结果
```

</details>

> 注：口播中「Mike Pocac」= Matt Pocock（发音误差）；「大弦」= 大神；「农所版」= 浓缩版；「优种」= 臃肿。
