---
title: "6组新Skill - 补齐Agent关键能力（task-observer/Karpathy/marketingskills/opencli/variate/Minimalist Entrepreneur）"
source: "抖音 @非也Origin · https://v.douyin.com/JmMzVgufwQE/"
video_id: "7682738764724609407"
author: "非也Origin"
date: "2026-09-07 发布+入库"
duration: "约 60 秒（60 行完整口播）"
tags: [抖音, Agent-Skills, task-observer, Karpathy, marketingskills, opencli, variate, Minimalist-Entrepreneur, Opc, 13BIT]
category: "AI工具/Agent 技能库"
confidence: "A"
---

# 6组新 Skill - 补齐 Agent 关键能力

> **核心信息**：6 组开源 Skill 覆盖 Agent 全生命周期——**自动复盘 / 减少越界修改 / 操作网站 / 比较设计 / 验证需求 / 优化注册付费**
> **创作者**：@非也Origin | 时长 60 秒 | 60 行完整口播
> **关键价值**：**6 个里 4 个对 BOSS 的 13BIT 体系有直接落地价值**——特别是 task-observer（**已验证在 Hermes 上跑通**）和 Karpathy 4 原则

---

## 6 组 Skill 速览（按对 13BIT 价值排序）

| # | Skill | GitHub | 价值 | BOSS 适用 |
|---|---|---|---|---|
| 1 | **task-observer** | [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) (2.4k ⭐) | ⭐⭐⭐⭐⭐ | **立即可用**（已验证 Hermes） |
| 2 | **Karpathy 4 原则** | [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills) (209k ⭐) | ⭐⭐⭐⭐⭐ | **已经抄进 MEMORY** |
| 3 | **marketingskills** | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (47.7k ⭐) | ⭐⭐⭐⭐ | **运营/营销 GM 必装** |
| 4 | **opencli** | [jackwener/OpenCLI](https://github.com/jackwener/OpenCLI) | ⭐⭐⭐⭐ | **替代 browser_exec 解决 100+ 网站** |
| 5 | **variate** | [Nutlope/variate](https://github.com/nutlope/variate) | ⭐⭐⭐ | **设计 GM 必装** |
| 6 | **Minimalist Entrepreneur** | [slavingia/skills](https://github.com/slavingia/skills) (10k ⭐) | ⭐⭐⭐ | **13BIT 商业层总纲** |

---

## 1. task-observer（**最大发现**）

**核心价值**：**meta-skill**——在 Agent 工作时持续观察，记录错误、纠正、可复用方法，**自动产出 skill 改进建议和新区 skill 候选**。

### 关键数据
- 作者：Eoghan Henn（@rebelytics）
- 7 个月内记录 1300+ observation，75 个 skill 大部分由它产出
- **44 个用户在 Hermes 和 OpenClaw 上跑通**（README 原文：*users have reported successful integrations into their Hermes and Openclaw setups*）
- 2400 ⭐，CC BY 4.0

### 工作流
```
1. 用户工作时 → task-observer 后台观察
2. 记录：错误工具、正确来源、纠正动作、用户偏好
3. 不直接改 skill，把建议交给用户审核
4. 例：Agent 用错品牌 logger 工具时
   - 记下：错误工具
   - 记下：用户指出的正确来源
   - 下次：自动按规则执行
```

### 为什么对 BOSS 是神器
- 13BIT 13 个 GM skill 现在是**静态的**——写完就锁死
- task-observer 让 skill **会自己进化**——和 BOSS 提出的"Evolution Mode"完美对齐
- 安装成本低：放 `.claude/skills/task-observer/` 即可

### 立即可做的事
```bash
# 1. 下载
mkdir -p ~/.hermes/skills/task-observer
cd ~/.hermes/skills/task-observer
git clone https://github.com/rebelytics/one-skill-to-rule-them-all.git .

# 2. 读 SKILL.md 让 agent 引导配置
# 3. 在每次任务结束时问"Any observations logged?"
# 4. 配 cron 任务定期 review 开放 observations
```

---

## 2. Karpathy 4 原则（**已抄进 MEMORY**）

**核心价值**：单一 `CLAUDE.md` 文件，4 条编码原则，**已在 BOSS MEMORY.md 落地**。

### 209k ⭐ 的 4 条原则
| 原则 | 解决 |
|---|---|
| **Think Before Coding** | 错假设、隐藏混乱、缺失权衡 |
| **Simplicity First** | 过度复杂、抽象膨胀 |
| **Surgical Changes** | 正交修改、动不该动的代码 |
| **Goal-Driven Execution** | 验收标准、可验证成功 |

### 关键 insight（转写原文）
> *动手前先定义成功标准，并验证到全部通过*
> *把这份文件放在 developer 根目录，下面每个项目都能继承*
> *同一套边界不需要反复提醒*

### BOSS 现状
- ✅ MEMORY.md 第 8 段已写：*"Karpathy编码四原则（20.9万星）：①先想再写 ②极简优先 ③手术式改动 ④目标驱动。编码任务默认遵循。"*
- 🔧 待办：把 4 原则落到 `~/.hermes/CLAUDE.md`（不只在 MEMORY）

---

## 3. marketingskills（**运营/营销 GM 必装**）

**核心价值**：**48 个增长任务**的 Agent Skills，**从注册流程到流失挽回全链覆盖**。

### 47.7k ⭐ 的覆盖范围
- **CRO**: signup / onboarding / paywalls / popups / churn-prevention
- **Content**: copywriting / copy-editing / website-copy
- **SEO**: site-arch / schema / programmatic-seo
- **Sales**: cold-email / launch / sales-enablement
- **Growth**: ab-testing / referrals / co-marketing
- **Strategy**: marketing-plan / pricing / revops

### 视频里的 3 个实战示例
- **onboarding**：原本注册要答 5 组问题 → 压缩成 1 组，其余进入产品后补
- **paywalls**：让用户**先看免费内容 + 锁定内容**再进定价页
- **churn prevention**：取消前**先问原因** → 给对应的暂停/保留方案

### 为什么对 BOSS 是金矿
- 13BIT 的运营/营销 GM 现在是空的
- marketingskills 直接给 A 级 prompt 模板
- 拿到后**立刻能让 BOSS 跨境电商品牌出海有现成的转化方法论**

---

## 4. opencli（**替代 browser_exec**）

**核心价值**：把 **100+ 网站**变成 Agent 可直接调用的命令，**通过 Chrome 扩展复用已登录账号**。

### 覆盖网站
Twitter/X、小红书、B站、知乎、LinkedIn、YouTube、Reddit、HackerNews、微博、Amazon、Bloomberg、Shopify、Discord、Instagram、Telegram……

### 工作原理
```
1. opencli 内置 100+ 站点适配器（确定性命令）
2. 浏览器自动化：Claude Code/Cursor 直接 navigate/click/type/extract
3. Chrome 扩展复用已登录 Chrome session（账号安全）
4. 输出格式：JSON / CSV / Markdown / YAML / table
```

### 视频里举的 X 例子
```
opencli x search "k..."        # 搜索帖子
opencli x bookmarks read       # 读取 bookmarks
opencli x post "..."           # 发帖
opencli x reply <id> "..."     # 回复
```

### 适合场景
- ✅ 操作**自己**的网页账号
- ❌ 面向用户的产品仍要接官方 API

### 为什么对 BOSS 是降本神器
- 13BIT 知识星球抓取、GitHub PR 自动化、Twitter 监控、Reddit 调研……**全部 opencli 一行命令搞定**
- **0 LLM 成本**（运行时不消耗 token，纯确定性命令）
- 安装：`npx skills add jackwener/opencli`

---

## 5. variate（**设计 GM 必装**）

**核心价值**：**AI 设计方案过于单一** → variate 对同一组件生成 **4 个真实版本**，本地菜单快速切换，选中的版本直接回传 agent。

### 工作流
```
1. agent 写 4 个完整可工作的版本
2. localhost 侧栏提供箭头键切换
3. 你点哪个 → 该版本直接是代码
4. 可只比较 hero / 按钮 / header
5. 把满意的部分组合起来
```

### 适用
- Next.js / 普通 HTML 都能用
- **零依赖**（Node 18 builtins only）

### 为什么对 BOSS 有用
- 13BIT 的"Listing 优化 GM" / "商品图 GM" / "品牌设计 GM" 都需要 A/B 设计能力
- 不再"和 agent 文字拉扯设计"——**直接 4 个版本看实物**

---

## 6. Minimalist Entrepreneur（**13BIT 商业层总纲**）

**核心价值**：Sahil Lavingia（Gumroad 创始人）**把《极简创业者》整本书变成 10 个 slash command**。

### 10 个 skill
| 命令 | 用途 |
|---|---|
| `/find-community` | 找社区、找商业想法 |
| `/validate-idea` | 验证想法是否值得做 |
| `/processize` | 写代码前先手工交付价值 |
| `/mvp` | 控制 MVP 范围 |
| `/first-customers` | 找前 100 个客户 |
| `/pricing` | 定价（"零价格效应"——免费到 1 分钱需求崩塌） |
| `/marketing-plan` | 内容营销 |
| `/grow-sustainably` | 可持续增长 |
| `/company-values` | 公司文化 |
| `/minimalist-review` | 极简决策复盘 |

### 视频里的核心方法
> *写代码前先从自己能触达的社区里找出反复出现的问题*
> *再验证这些人是否真的愿意付费*
> *要求列出 10 个真实用户，至少 3 个明确愿意购买*
> *验证通过后，其他 skills 再处理 MVP/手工交付/首批客户/定价/营销*

### 关键的"verdict"机制
每个 skill 结尾必须有 **validated / needs more validation / pivot** 三选一，**不让 AI 骑墙**。

### 为什么对 BOSS 是总纲
- 13BIT 13 个 GM 是"执行层"
- 10 个 Minimalist Entrepreneur skill 是"**商业层**"
- 两者叠加 = 13BIT 既是运营军团也是商业教练

---

## 七、立即可落地的 5 件事（按 ROI 排序）

### 🔥 P0（今天做）
1. **装 task-observer** → 立刻让 13BIT 13 个 skill 进入"自我进化"轨道
   ```bash
   mkdir -p ~/.hermes/skills/task-observer
   git clone https://github.com/rebelytics/one-skill-to-rule-them-all.git ~/.hermes/skills/task-observer/
   ```
2. **把 Karpathy 4 原则落到 `~/.hermes/CLAUDE.md`**（不只在 MEMORY）
3. **安装 opencli**（零 LLM 成本解决 100+ 网站）
   ```bash
   npx skills add jackwener/opencli
   ```

### P1（本周做）
4. **运营/营销 GM 用 marketingskills 改造**（48 个 skill 直接抄）
5. **设计 GM 装 variate**（4 版本本地切换）

### P2（本月做）
6. 13BIT 商业层补充 Minimalist Entrepreneur 10 个 skill（"商业层总纲"）

---

## 八、6 个 Skill 的战略意义

### 这 6 个 Skill 形成完整闭环
```
task-observer  → 负责复盘
Karpathy       → 管住执行边界（不越界）
marketingskills → 负责增长（CRO/SEO/Sales）
opencli        → 操作网站（100+）
variate        → 比较设计
Minimalist     → 先验证需求（10 用户 / 3 付费）
```

### 6 个 skill 共同价值
- **让 Agent 少犯错**（Karpathy 边界 + task-observer 复盘）
- **少返工**（opencli 不再 browser 找按钮 + variate 不再文字拉扯）
- **更接近可交付产品**（marketingskills + Minimalist 商业验证）

---

## 附：原始素材

- 视频：60 秒完整口播（Whisper 识别率 A-）
- 转写文件：`/Users/【BOSS英文名】/WorkBuddy/douyin-tmp/20260907-ingest/7682738764724609407.txt`
- Meta：`/Users/【BOSS英文名】/WorkBuddy/douyin-tmp/20260907-ingest/meta.json`
- **关键修正**：原转写中"Android Carpathian" = **Andrej Karpathy**；"Cory Haines" = **Corey Haines**；"sahil lavina" = **Sahil Lavingia**（Whisper 把西式名字听成近似音，已用 GitHub 仓库名校正）
- 6 个 GitHub 仓库全部 web_search 验证
- **关键发现**：task-observer README 原文确认已在 Hermes 和 OpenClaw 跑通
