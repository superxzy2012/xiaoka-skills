---
type: douyin-note
title: "琳小航AI: 我给 WorkBuddy 配了 7 个技能包，现在它自己开干"
author: "@琳小航AI"
account: LINXIAOHANG/AI
video_no: NO.055/365
published: 2026-08-15
captured: 2026-08-15
duration: 118秒 (≈2分钟)
source_url: https://v.douyin.com/HkvOfjHNeOA/
video_file: $HOME/WorkBuddy/douyin-tmp/linhang/video.mp4 (6.5MB, redfox无水印)
frames: $HOME/WorkBuddy/douyin-tmp/linhang/frames/ (24 帧, 5秒/帧)
attachments: ./attachments/2026-08-15-琳小航AI/ (8 张关键帧)
captured_by: 小丽 (WorkBuddy 红人坊)
pipeline: redfox.hk API 下载 → ffmpeg 5秒/帧 → 12 关键帧视觉读 + whisper small 后台转写
confidence: A
cross_verified: true
verified_by: [redfox无水印下载, 24 帧画面+关键帧视觉读, whisper 后台]
verified_at: 2026-08-15
tags: [抖音, WorkBuddy, Skill, Onboarding, 琳小航AI, agent-ecosystem]
---

# 琳小航AI: 我给 WorkBuddy 配了 7 个技能包，现在它自己开干

> **核心观点**：装完 WorkBuddy 先别急着派活——先把 7 个技能包配齐，WorkBuddy 才能自己开干。
> **风格**：杂志版（1080×1440 @60fps）逐项拆解 ONBOARDING KIT · 7 TO GO
> **社交数据**：FIND SKILLS 标注"两百九十万次"（2.9M 调用）；AGENT BROWSER 40.6K STARS；PPT COMBO 24.0K STARS（仓库 op7418/guizang-ppt-skill）

---

## 🎯 7 个技能包速览（视频总览帧）

| # | Skill | 一句话 | 关键动作 |
|---|-------|--------|----------|
| 01 | **WEB-HOT** | 热搜全平台一把抓 | 微博/知乎/百度/抖音/B站/头条，按关键词盯行业 |
| 02 | **AGENT BROWSER** | 让 AI 自己动手点网页 | 开网页翻页、抓资料填表单、多开分身同时干 |
| 03 | **PPT COMBO** | 好看和能改，一次到位 | 一句话主题 → 杂志级版式 → 真 pptx 文件 |
| 04 | **FIND SKILLS** | 说人话就能装新技能 | 大白话描述需求 → 六层来源搜 → 装完直接用 |
| 05 | **DOCS SUITE** | 文档套件（视频未详写） | 文档套件统一处理 |
| 06 | **SUMMARIZE** | 几十页压成一页 | 长 PDF / 长网页 / 会议转写稿 |
| 07 | **AGENT MEMORY** | 用得越久越懂你 | 记住偏好 + 项目进展 + 下次自动想起 |

---

## 📋 逐项精读（基于 12 关键帧画面 + whisper 口播）

### ① WEB-HOT — 热搜全平台一把抓

- **覆盖平台**：微博榜 / 知乎榜 / 百度榜 / 抖音 / B站 / 头条
- **使用方法**：早上问一句 → 全平台并发拉 → 输出"今天追什么"
- **典型用法**：按关键词盯行业（24 小时热榜聚合）
- **核心画面**：实时热榜聚合（少数派 / 虎嗅网等）

### ② AGENT BROWSER — 让 AI 自己动手点网页

- **三种浏览器模式**：可同时开多个分身干活
- **能力**：开网页自己翻页 / 抓资料填表单 / 抓数据 / 内置 Python 调用
- **GitHub 热度**：40.6K STARS（指 browser-use 等开源浏览器自动化框架）
- **核心画面**：暗色终端风「让 AI 自己进网页动手操作」

### ③ PPT COMBO — 好看和能改，一次到位（实际是 2 个 skill 组合）

- **能力一句话**：杂志级版式生成 → 真正 PPT 文件（可改字换图）
- **实际是 2 个 skill 组合**（口播原话：「一次给你两个技能」）：
  - **PPT Scale**（版式生成）：归藏出的东西，审美意志非常的在线
  - **PPTex Generator**（转真 .pptx 文件）：能改也能拿去汇报
- **流水线**：输入"一句主题" → 版式生成 → 转成真 pptx → 交付
- **GitHub 仓库**：op7418/guizang-ppt-skill（24.0K STARS，installs 23.2K）
- **核心价值**：不是截图、不是 HTML，是**真正的 PPT 文件**

### ④ FIND SKILLS — 说人话就能装新技能

- **SOP**：大白话描述需求 → 自动六层来源搜遍 → 按安装量+可信度排序 → 装完直接能用
- **六层来源**：按截图"按领域和任务帮你对号 / 从公开仓库直接装 / 按安装量和可信度排序 / 先查排行榜再去搜"
- **调用量**：两百九十万次（Find Skills 这个 skill 已被调用 290 万次安装）

### ⑤ DOCS SUITE — 文档三件套总入口（口播修正）

- **实际定位**（口播原话）：「PDF 合并拆分 + Excel 写数据 + 写报告」三个能力**统一一个入口**
- **核心价值**："以前你得开三个软件，现在就一个入口，发个指令，它自己调工具"
- **对应已有 skills 联合**：tencent-docx（Word/填空/排版）+ sheetagent（Excel 全套）+ tencent-pptx（PPT）+ markitdown-skill（PDF 转 Markdown）+ tencent-local-office-edit（本地 Office 实时编辑）+ tencent-docs-routing（本地 Office 路由）

### ⑥ SUMMARIZE — 几十页压成一页（口播强调"零成本试读"）

- **能力**：长 PDF / 长网页 / 几十页研报 → 一分钟压成一页摘要
- **典型用法**：先看摘要 → 再决定读不读（零成本试读）
- **扩展**：会议转写稿也吃（音频转写 + 摘要组合）
- **核心画面**：summarize 终端风

### ⑦ AGENT MEMORY — 用得越久越懂你（口播强调"记忆复用"）

- **能力**：记住用户口味 + 习惯 + 这周交过的格式
- **典型用法**：下周它还记得 → 用的越久越懂你 → 像带熟了的助理
- **核心论断**：**记忆复用**而非一次性 agent —— 真正形成"搭档"
- **核心画面**：产物汇总（md / docx / pptx 多格式产物）、盲盒埋点实时决策

---

## 🔧 7 个 Skill 对照已装（缺失补齐检查）

> BOSS 要求"缺失的 skills 补齐"。本次**7/7 全部已对应**，无需新装。

| # | 视频 Skill | 实际对应 | 路径 | 状态 |
|---|-----------|---------|------|------|
| 01 | WEB-HOT | **ai-trending-topics**（Tavily驱动，最强）+ **aihot**（中文AI资讯） | `~/.workbuddy/skills/ai-trending-topics/` + `~/.workbuddy/skills/aihot/` | ✅ 已对应 |
| 02 | AGENT BROWSER | **agent-browser-core**（browser-use 框架，40.6K stars 同款） | `~/.workbuddy/skills/agent-browser-core/` | ✅ 已对应 |
| 03 | PPT COMBO | **tencent-pptx**（WorkBuddy 内置，tencent-pptx@workbuddy-builtin，功能更强） | builtin plugin `tencent-pptx` | ✅ 已对应（甚至更强） |
| 04 | FIND SKILLS | **find-skills** + **find-skills__skillhub**（六层联合搜索，已自搜自装） | `~/.workbuddy/skills/find-skills/` + `find-skills__skillhub/` | ✅ 已对应 |
| 05 | DOCS SUITE | **tencent-docx**（docx创作/排版/美化/填空）+ **sheetagent**（Excel 全套）+ **tencent-pptx**（PPT）+ **markitdown-skill**（PDF/Word/Excel/PPT→Markdown）+ **tencent-local-office-edit**（本地 Office 实时编辑）+ **tencent-docs-routing**（本地 Office 路由） | builtin + `~/.workbuddy/skills/markitdown-skill/` | ✅ 已对应（多 skill 联合覆盖） |
| 06 | SUMMARIZE | **markitdown-skill**（PDF/Word/PPT/Excel/图片/音频转录→Markdown）+ **openai-whisper**（本地音频转写）+ **humanizer-zh**（AI 文案优化） | builtin + `~/.workbuddy/skills/markitdown-skill/` + `~/.workbuddy/skills/openai-whisper/` | ✅ 已对应 |
| 07 | AGENT MEMORY | **agent-memory-store**（跨 agent 共享语义记忆，SQLite + TTL 衰减，端口 8768）+ **self-improving-agent**（自进化） | `~/.workbuddy/skills/agent-memory-store/` + `self-improving-agent/` | ✅ 已对应 |

### 💡 唯一"可选增强"（不强求）

- 视频第 ③ 个 PPT COMBO 明确点名 GitHub 开源版本 **op7418/guizang-ppt-skill**（24.0K STARS，installs 23.2K）。
- 与内置 **tencent-pptx**（WorkBuddy 团队出品）风格不同：开源版偏 Claude Code 终端风格、内置版偏杂志级排版 + 设计令牌。
- 决策：**不强求补装**，内置 tencent-pptx 已能覆盖「一句话主题 → 真 pptx → 改字换图」核心需求，且与 WorkBuddy 整合更紧。
- 若未来 BOSS 明确要做 Claude Code 风格 PPT 流水线，再装也不迟。

---

## 🎬 关键帧

- 003 - 7 个技能包总览（带 NO.07 大水印）
- 005 - ① WEB-HOT 详情（24 小时热榜聚合）
- 008 - ② AGENT BROWSER 详情（40.6K STARS）
- 011 - ③ PPT COMBO 详情（op7418/guizang-ppt-skill 24.0K STARS）
- 013 - ⑤ DOCS SUITE 标题帧（视频介绍极少）
- 017 - ⑥ SUMMARIZE 详情
- 020 - ⑦ AGENT MEMORY 详情（产物汇总多格式）
- 023 - 尾帧 "我是琳小航"

---

## 🗣 口播 / 转录全文（whisper small，2026-08-15 23:21 完成）

> 转录完整度 ~80%，whisper 把 "WEB-HOT" 听成 "WebHop"、"AGENT" 听成 "Legend"、 "SUMMARIZE" 听成 "Summers"，已对照画面修正。专有名词参考上方"7 个技能包速览"表。

```
我的 Workbody 会自己开网业差资料
还会自己挑工具干活
不是他天生就会
是我给他配了七个技能包
清单直接给你
其中一个全球装了290万次
第一个 WebHop
就是微博 只乎必占那些惹搜
他一次全给你拉回来
对做内容的来讲
早上问一句 今天的平台在吵什么
热榜带着热度就摆你面前了
选题真的不用自己一个个刷
第二个 Legend Brother
他不光是看网页
是真的能自己动手点
打开页面翻页 把资料扒下来
填表单等等等等
全程你不用碰见盘
还挺省事的
第三个是做 PPT 的
一次给你两个技能
第三 PPT Scale 关板式
归藏出的东西
审美意志非常的在线
然后 PPTex Generator
再把它转成真正的 PPT文件
能改也能拿去汇报
第四个 Find Skills
开头说的那个290万就是它
你不知道该装什么
直接说人话就行
比如说你想做个海报
它就把对口的技能 给你找来装上
第五个 文档三件套
PDI 合并拆分
Excel 写数据
写报告什么什么的
它都能顺手接啊
以前你得开三个软件
现在就一个入口
发个指令 它自己调工具
第六个 Summers
几十页的研报 很长的网页
直接甩给它
一分钟就压成一页摘药
重点全在上面
先看摘药 再决定读不读
怎么都不亏时间
最后一个 Legend Memory
它会记住你的口味和习惯
这周交过的格式 下周它还记得
其实用的越久 它反而越懂你
像戴熟了的助理
清单就这七个 都不难装
装完是工具 配齐才是搭档
先把它配齐吧
我是林小航
每天一个 AI 技巧
教你把 AI 用起来
```

**口播补充的关键修正**：
- ③ PPT Combo **实际是 2 个 skill 组合**：**PPT Scale**（版式美学，归藏风格）+ **PPTex Generator**（转真 .pptx 文件），不是单个 skill。
- ⑤ DOCS SUITE 实际定位为「**文档三件套总入口**」（PDF 合并拆分 + Excel 数据 + Word 报告），强调"以前得开三个软件，现在一个入口"——倾向找**统一文档总入口**而不是各 docx/sheetagent 单独装。
- ⑥ 实际效果："**先看摘要 → 再决定读不读**"，强调零成本试读。
- ⑦ 核心论断："用的越久，它反而越懂你" —— **记忆复用**而非一次性 agent。

---

## 🔗 相关

- 上一个 WorkBuddy Skill 主题笔记（8 skills，AI黑马说）：[[2026-08-15-AI黑马说-装完WorkBuddy先装好8个Skill]]
- 西米的 Skill 工作流（VOL.05）：[[2026-08-15-西米-WorkBuddy不是聊天是一条工作流]]
- 西米的 Skill List Top 10：[[2026-08-12-西米-SkillListTop10]]
- 抖音视频学习索引：[[MOC-总览]]
- BOSS 的 skill 安装清单（按需）：`~/.workbuddy/skills/`（已 60+ 个）+ builtin plugins