---
title: "GitHub 排名最高的9个 Skill 拆解"
source: "https://v.douyin.com/Lbac9Ado82Q/"
platform: douyin
type: image-text
author: "叫我火华同学（AIGC版）"
published: 2026-09-02
captured: 2026-09-03
tags: [douyin, skill, github, ai-agent, 提炼]
confidence: A
summary: "火华同学拆解了 GitHub 上 Star 最高的 9 个 Agent Skill 仓库，从工程方法论、Agent 工程系统、反馈回路、编码规则、官方示例、专家团队、UI/UX设计、知识图谱到 Token 压缩，逐个说明核心思路、适用人群和使用边界。"
---

# GitHub 排名最高的9个 Skill 拆解

> [!abstract] 摘要
> 火华同学从 GitHub 上 Star 最高的一批 Skill 仓库中精选 9 个，按 Star 数从高到低逐一拆解：核心不是抄文件，而是抄高手的做事方法。每个 Skill 都标注了全名、重点、适合谁、使用边界。

## 9 个 Skill 总览（按 Star 从高到低）

| # | 仓库 | Star 数（2026.09.02） | 类别 |
|---|------|---------------------|------|
| 01 | obra/superpowers | 约 28.0 万 | 工程方法论 |
| 02 | affaan-m/ECC | 约 24.6 万 | Agent 工程系统 |
| 03 | mattpocock/skills | 约 24.4 万 | 工程反馈回路 |
| 04 | multica-ai/andrej-karpathy-skills | 约 20.9 万 | 极简编码规则 |
| 05 | anthropics/skills | 约 17.3 万 | 官方 Skill 示例 |
| 06 | garrytan/gstack | 约 13.1 万 | 专家团队工作流 |
| 07 | nextlevelbuilder/ui-ux-pro-max-skill | 约 12.4 万 | UI/UX 设计智能 |
| 08 | Graphify-Labs/graphify | 约 11.3 万 | 可查询知识图谱 |
| 09 | JuliusBrussee/caveman | 约 10.2 万 | Token 压缩 |

---

## 01 · obra/superpowers — 工程方法论

**核心**：一套完整的软件开发方法论，把 7 道工程纪律装进 AI，而不是零散的 Skill。

7 道纪律：
1. 头脑风暴
2. 隔离工作区
3. 拆解计划
4. 分任务执行
5. 测试驱动
6. 代码审查
7. 收尾合并

> 需求没确认，不急着动代码。先想清楚，再开始。

- **适合**：想让 Coding Agent 长时间推进、又不偏离设计的人
- **边界**：流程是强制性的；小改动也可能显得偏重

![[20260903-Lbac9Ado82Q/img_02.png]]

---

## 02 · affaan-m/ECC — Agent 工程系统

**核心**：不只加 Skill，直接装一套工程操作系统（Agent Harness）。把规划、测试、审查、记忆、安全和持续学习组织成一套完整体系。

关键数字：
- **68 个 Agents**：覆盖不同职责的智能体角色
- **286 个 Skills**：可复用的工程能力模块
- **94 个命令入口**：统一入口，快速调用与编排

内置系统：
- **记忆系统**：对话记忆 / 项目记忆 / 知识库
- **安全防护**：AgentShield / 规则引擎 / 权限控制
- **持续学习**：反馈闭环 / 指标追踪 / 能力进化

- **适合**：希望一次配置完整工程协作层的人
- **边界**：Claude Code 支持最完整；其他编辑器能力并不完全等价
- **⚠️ 安全提醒**：只从官方仓库与官方安装渠道获取

![[20260903-Lbac9Ado82Q/img_03.png]]

---

## 03 · mattpocock/skills — 工程反馈回路

**核心**：真工程师的私货，不是漂亮模板。围绕 Coding Agent 的四个真实失败点，设计可重复调用的反馈回路。

| 失败点 | 对应 Skill |
|--------|-----------|
| 没对齐 | grill-me / grill-with-docs |
| 说太多 | 建立 CONTEXT.md（共同语言） |
| 代码不工作 | tdd / diagnosing-bugs |
| 越写越乱 | codebase-design / code-review |

**CONTEXT.md**：把目标、假设、验收标准拉到明面上，用项目专属上下文减少解释成本与认知噪音。

- **适合**：想长期维护真实代码库，而不是只追求出活速度的人
- **边界**：先运行 setup；效果依赖项目里的测试、类型与上下文

![[20260903-Lbac9Ado82Q/img_04.png]]

---

## 04 · multica-ai/andrej-karpathy-skills — 极简编码规则

**核心**：一个文件，限制 AI 最常犯的 4 种错。把 Karpathy 对 Coding Agent 常见问题的观察，压成一份 CLAUDE.md 规则。

四条规则：
1. **Think Before Coding** — 先暴露假设：先写清假设、范围和不确定点，再动手写代码
2. **Simplicity First** — 只写必要代码：拒绝过度设计与未来扩展
3. **Surgical Changes** — 只改相关行：不随意重构、不格式化全文件
4. **Goal-Driven Execution** — 先定义验收：以目标驱动每一步执行

> 结果：更少无关改动 · 更少过度设计 · 更干净的 Diff

- **适合**：已有项目、修 Bug、重构和需要干净提交的人
- **边界**：偏谨慎；简单小改动不必每次都走完整流程
- **⚠️ 注意**：这是 multica-ai 仓库，不是 Karpathy 官方仓库

![[20260903-Lbac9Ado82Q/img_05.png]]

---

## 05 · anthropics/skills — 官方 Skill 示例

**核心**：Anthropic 的 Agent Skills 示例、规范、模板与复杂文档 Skill 参考实现。

三大组成：
- **skills**：创意、开发、企业与文档示例（丰富的官方 Skill 示例）
- **spec**：Agent Skills 规范（定义结构、能力与接口）
- **template**：创建 Skill 的起点（起始模板 + 文件骨架）

生产中使用的四类文档 Skill：docx / pdf / pptx / xlsx

> 关键认知：每个 Skill 都是包含 SKILL.md、脚本与资源的独立文件夹。

- **适合**：学习复杂 Skill 怎么组织，或处理 Office / PDF 文件
- **边界**：文档四件套是 source-available，不等于全部开源；关键任务必须实测

![[20260903-Lbac9Ado82Q/img_06.png]]

---

## 06 · garrytan/gstack — 专家团队工作流

**核心**：Garry Tan 的高主张工作流：把一次开发冲刺拆成一支专家团队，每个 Skill 扮演一个明确岗位，并按冲刺顺序交接。

七步角色：
1. **CEO** — 重审问题与产品范围（Think）
2. **工程经理** — 架构、数据流与测试（Plan）
3. **设计师** — 设计评审与方案探索（Build）
4. **Staff Engineer** — 代码审查与排错（Review）
5. **QA / 安全 / 发布 / SRE** — 验证上线（Test / Ship）
6. **Reflect** — 复盘反思

> 它强调流程交接，不是把一堆命令平铺在桌面。

- **适合**：要从模糊想法一路推进到上线验证的产品团队
- **边界**：方法强、角色多；简单项目可能过重

![[20260903-Lbac9Ado82Q/img_07.png]]

---

## 07 · ui-ux-pro-max-skill — UI/UX 设计智能

**核心**：不是给 AI 审美，是给它可检索的设计规则。按产品类型搜索风格、配色、字体、结构与反模式，再生成完整设计系统。

资源规模：
- **79 种**可搜索风格
- **192 套**产品配色
- **74 组**字体搭配
- **25 种**图表建议
- **22 个**技术栈
- **119 条**UX 指南
- **192 条**行业推理规则
- 含交付检查

输出公式：页面结构 + 风格 + 配色 + 字体 + 动效 + 反模式

- **适合**：程序员、独立开发者和跨技术栈界面项目
- **边界**：开源基础版提供设计规则，不等于自动生成成熟品牌资产

![[20260903-Lbac9Ado82Q/img_08.png]]

---

## 08 · Graphify-Labs/graphify — 可查询知识图谱

**核心**：别在老项目里盲搜，先把它变成一张图。把代码、文档、PDF、图片与视频映射成可查询的知识图谱。

三大核心能力：
1. 本地 AST 解析代码（不靠 LLM）
2. 每条边标记 EXTRACTED / INFERRED
3. 不是向量库，可以 query / path / explain

三份开箱即用输出：
- `graph.html` — 可视化接口
- `GRAPH_REPORT.md` — 关键发现
- `graph.json` — 继续查询

> 核心：从"逐文件翻找"变成"沿关系问路"。

- **适合**：接手老代码库、跨文档调查和复杂项目导航
- **边界**：文档与媒体的语义处理可能调用模型；需要 Python 环境
- 旧地址 safishamsi/graphify 已重定向到 Graphify-Labs/graphify

![[20260903-Lbac9Ado82Q/img_09.png]]

---

## 09 · JuliusBrussee/caveman — Token 压缩

**核心**：不只让 AI 少说，现在也让它少读。Caveman 2 分成两层：Skill 压缩输出，Proxy 压缩输入。

| 层 | 作用 | 效果 |
|----|------|------|
| 输出层（Skill） | 让回复更短；代码、命令、错误保持准确 | 输出平均减少 65% |
| 输入层（Proxy） | 压缩 JSON、日志、代码、Diff 与搜索结果；支持精确恢复被折叠内容 | 输入减少 33.2% |

仓库自己写明的边界：
- Skill 每轮会增加约 1-1.5k 输入 Token
- 本来就很短的任务可能省不到，甚至净增加
- 最稳定的收益是可读性与速度，省钱只是附加

许可：MIT + BSL-1.1 分层

- **适合**：长日志、长上下文、输出啰嗦的 Agent 工作流

![[20260903-Lbac9Ado82Q/img_10.png]]

---

## 封面

![[20260903-Lbac9Ado82Q/img_01.png]]

## 来源

- 抖音链接：https://v.douyin.com/Lbac9Ado82Q/
- 作者：叫我火华同学（AIGC版）
- 发布时间：2026-09-02 08:58:04
- 抓取时间：2026-09-03
- 形式：图文帖（10 张图）

---

## 🧪 真实性核验（2026-09-03 实测）

> 9 个仓库**全部真实存在**，Star 数与抖音说法基本吻合（误差在 1% 以内）。

| # | 仓库 | 抖音说 | 实测 Star | 吻合度 | 本地研究目录 |
|---|------|--------|----------|--------|-------------|
| 01 | obra/superpowers | ~28.0万 | 280,801 | ✅ 99.7% | `~/WorkBuddy/github-skills-research/` |
| 02 | affaan-m/ECC | ~24.6万 | 246,284 | ✅ 99.9% | 同上 |
| 03 | mattpocock/skills | ~24.4万 | ~245k | ✅ 99.6% | 同上 |
| 04 | multica-ai/andrej-karpathy-skills | ~20.9万 | ~209,364 | ✅ 99.8% | 同上 |
| 05 | anthropics/skills | ~17.3万 | ~173,214 | ✅ 99.9% | 同上 |
| 06 | garrytan/gstack | ~13.1万 | 130,924 | ✅ 99.9% | 同上 |
| 07 | nextlevelbuilder/ui-ux-pro-max-skill | ~12.4万 | 124,316 | ✅ 99.8% | 同上 |
| 08 | Graphify-Labs/graphify | ~11.3万 | 113,994 | ✅ 99.1% | 同上 |
| 09 | JuliusBrussee/caveman | ~10.2万 | 102,600 | ✅ 99.6% | 同上 |

## 📦 已落地动作

### ✅ 已完成
1. **Karpathy 编码四原则** — 已写入记忆，作为编码任务默认遵循的铁律（先想再写 / 极简优先 / 手术式改动 / 目标驱动）
2. **4 个核心仓库已 clone 到本地** — `~/WorkBuddy/github-skills-research/`（karpathy-skills、caveman、mattpocock-skills、anthropics-skills）
3. **9 个仓库真实性全部核验通过** — Star 数数据可信

### ⏳ 待审批后执行
1. **caveman Token 压缩** — 有 Hermes proxy 适配，通过把 `CUSTOM_BASE_URL` 指向 caveman proxy 实现全链路 token 压缩（输入-33.2% / 输出-65%）。属于架构级改动，需 BOSS 审批后安装
2. **obra/superpowers** — 原生支持 Hermes 插件，但安全扫描 226 项高危阻断（大量 shell 脚本）。如需安装需 `--force` 绕过，不建议默认操作
3. **ECC / gstack** — 主要面向 Claude Code / Codex 用户，Hermes 侧价值待评估

## 💡 关键发现

- **caveman 工程最完善**：不是一个简单的 prompt，而是包含 Go 语言 proxy、MCP server、20+ 子 skill、浏览器扩展的完整体系，且官方维护 Hermes profile
- **anthropics/skills 文档四件套含金量高**：docx/pdf/pptx/xlsx 是 Claude 官方生产级实现，比随便找的开源库质量高得多（但 source-available 不是完全开源）
- **graphify 技术路径独特**：本地 AST 解析 + 知识图谱，不靠向量库，在大型代码库理解场景有差异化价值
- **mattpocock/skills 工程味最浓**：围绕"真实失败点"设计反馈回路，而不是堆功能，理念上和 BOSS 的工程偏好匹配
