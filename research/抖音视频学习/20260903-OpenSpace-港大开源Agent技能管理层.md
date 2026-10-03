---
title: "OpenSpace — 港大开源 AI Agent 技能管理层（检索/评估/分享/进化四步闭环）"
source: "https://v.douyin.com/DgWeZh4LG-s/"
platform: douyin
type: video
author: "AI的那三亩地"
published: 2026-09-03
captured: 2026-09-03
tags: [AI工具, Agent技能, 技能管理, 港大, OpenSpace, 自进化]
confidence: A
---

## 核心信息

- **项目名**：OpenSpace
- **出品方**：港大数据科学实验室（HKUDS）
- **GitHub**：[HKUDS/OpenSpace](https://github.com/HKUDS/OpenSpace)
- **Stars**：~7.5k（GitHub Trending #8）
- **许可**：MIT
- **定位**：AI Agent 的技能管理层（Skill Management Layer）
- **一句话**：给 Agent 加一层技能管理，检索→评估→分享→进化，让技能越用越好用

---

## 解决的问题

你是不是装了一堆 skill 放在那吃灰，用的时候不知道选哪个？

| 痛点 | OpenSpace 的解法 |
|------|----------------|
| 技能过时跟不上 | 基于实际结果持续评估，自动淘汰失效技能 |
| 盲目分享无证据 | 每个技能带运行记录、成功率、历史变更 |
| 重复犯错不学习 | 失败自动修复，成功自动沉淀为新技能 |
| 多 Agent 技能不互通 | 统一技能库，所有 Agent 共享 |
| 技能变更多失控 | 每次变更可审查、可回滚、有完整历史 |

---

## 四大核心能力

### 1. 🔍 检索（Retrieve）
- 为每个任务自动匹配最合适的技能
- 不看技能描述写得多漂亮，看实际运行记录
- 基于 embedding 的语义搜索 + 质量排序

### 2. ✅ 评估（Evaluate）
- 追踪每次运行：被选中 → 被应用 → 完成 → 被回退
- 监控依赖：工具失效、变慢、变危险时自动标记
- 真实任务结果作为评估依据，不是人工打分
- 优先选择持续完成真实任务的技能

### 3. 🤝 分享（Share）
- 成功的工作流自动转化为团队知识
- 跨所有 Agent 的统一技能库（Claude Code / Codex / OpenClaw / Hermes / nanobot）
- 技能带完整上下文：包结构、可见性、历史、质量信号
- 私有化部署，数据完全受控

### 4. 🔄 进化（Evolve）— 最狠的一步
- **自动修复**：技能失败时自动分析原因并修复
- **自动衍生**：成功的工作流自动沉淀为新技能
- **自动淘汰**：不再有效的技能自动降级/移除
- **可审查**：每次变更都有记录，可人工审核，不会失控

> 不是提示词仓库，而是让你的技能越用越好用的活系统。

---

## 技术架构

### 支持的 Agent 平台
- Claude Code
- Codex
- OpenClaw
- **Hermes**（原生支持）
- nanobot

### 核心模块
```
openspace/
├── skills/              # 技能管理核心
│   ├── evolver.py       # 进化引擎（FIX/DERIVED/CAPTURED 三种触发）
│   ├── patch.py         # 多文件补丁应用
│   └── skill_utils.py   # 技能工具函数
├── entrypoints/
│   ├── cli/             # openspace 命令行
│   ├── dashboard/       # Web 仪表盘
│   ├── gateway/         # 网关服务
│   ├── mcp/             # MCP 服务
│   └── tui/             # 终端 UI
├── communication/       # 多通道网关（飞书/WhatsApp）
└── platforms/           # 平台抽象层
```

### 运行时目录
```
.openspace/              # embedding 缓存 + 技能数据库
logs/                    # 执行日志 + 录制
```

---

## v2 新特性（2026-07-17）

- 📦 基于包的技能浏览（Package tree）
- 📊 技能质量摘要（Quality summaries）
- 📈 任务轨迹上传（Task-trace uploads）
- 🎨 全新仪表盘 + TUI 界面
- 🔍 Skill Wiki：共享技能变成可搜索的包树，带来源和质量上下文

---

## 与 Hermes 的关系

### 高度互补
OpenSpace 解决的正是我们一直在手动做的事情：

| 我们现在的做法 | OpenSpace 的做法 |
|--------------|----------------|
| 技能多了靠记忆找 | 自动语义检索 + 质量排序 |
| 踩坑后记到 MEMORY.md | 自动评估 + 失败记录 + 自动修复 |
| 新技能手动封装 | 成功工作流自动衍生为新技能 |
| 技能多了不知哪些有用 | 基于实际运行数据自动淘汰 |

### 原生支持 Hermes
README 明确列出 Hermes 作为支持的 Agent 之一，有 `host_skills` 接入指南。

---

## 安装与使用

> ⚠️ PyPI 上的 `openspace` 是另一个天体动力学包，别装错！

### 正确安装方式
```bash
# 从 GitHub 源码安装
pip install git+https://github.com/HKUDS/OpenSpace.git

# 或 clone 后安装
git clone https://github.com/HKUDS/OpenSpace.git
cd OpenSpace && pip install -e .
```

### 主要命令
```bash
openspace --help              # 查看帮助
openspace-dashboard           # 启动 Web 仪表盘
openspace-gateway             # 启动网关服务
openspace-mcp                 # 启动 MCP 服务
```

---

## 对 13BIT / 我们的价值

### 直接价值
1. **技能自动进化** — 不用手动复盘封装，成功的自动沉淀
2. **质量可控** — 每个技能有真实运行数据，不是凭感觉
3. **多 Agent 共享** — Hermes / OpenClaw / 飞书 bot 共用一套技能库
4. **失败不白踩** — 每次失败都是进化的输入

### 风险与注意事项
- ⚠️ 项目比较新（2026-03 开源），稳定性待验证
- ⚠️ 进化是双刃剑：自动修改技能可能引入问题，需要人工审核机制
- ⚠️ 需要 embedding 模型 + 本地数据库，有一定资源消耗
- ⚠️ 与 Hermes 原生技能体系的集成深度待实测

---

## 关键截图

| 项目主页 | 四大能力 |
|---------|---------|
| ![项目主页](../attachments/20260903-DgWeZh4LG-s/f_14.png) | ![四大能力](../attachments/20260903-DgWeZh4LG-s/f_05.png) |

| 技能库 | v2 新特性 |
|-------|----------|
| ![技能库](../attachments/20260903-DgWeZh4LG-s/f_15.png) | ![v2新特性](../attachments/20260903-DgWeZh4LG-s/f_12.png) |

---

## 完整口播

> 你在 Agent 是不是装了一堆 skill 后放在那吃灰，使用的时候也不知道用哪一个？赶紧给你的 Agent 装 OpenSpace，它给 Agent 加了一层技能管理层。总共四步：第一步是检索，为每个任务找到合适的技能；第二步是评估，不看技能写得多漂亮，只看真跑中有没有用，有没有回退，全凭证据；第三步是分享，一个 Agent 学会的，全体 Agent 共享；第四步是进化，也是最狠的一步，实现了技能自动修复，再把成功经验自动沉淀为新的技能。它不是一个提示词仓库，而是让你的技能越用越好用。Claude Code、Codex 以及国内的主流 Agent 都能接入。真心建议你收藏，别等你的 Agent 在原地踏步的时候才后悔。

---

**真实性核验**：✅ 已验证
- GitHub 仓库存在：HKUDS/OpenSpace，~7.5k Stars，MIT 协议
- 港大数据科学实验室出品，GitHub Trending #8
- v2 于 2026-07-17 发布，与视频描述一致
- 原生支持 Hermes，README 有明确说明
- 安装注意：PyPI 的 openspace 是另一个包，必须从 GitHub 源码安装
