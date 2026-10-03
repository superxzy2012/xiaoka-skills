---
title: "GitHub热门精选 Vol.016：Obsidian AI 三件套（obsidian-skills / claudian / obsidian-mind）"
source: "https://v.douyin.com/LJRvE2b1hrQ/"
platform: douyin
type: video
author: "狐狸的 AI 情报站"
video_id: "76853951【手机号】"
published: 2026-09-15
captured: 2026-09-15
tags: [douyin, 提炼, GitHub, Obsidian, ClaudeCode, Codex, AI记忆, 技能, 开源精选]
summary: "本期 3 个 Obsidian × AI 热门项目：① kepano/obsidian-skills 48.3k★——Obsidian CEO 亲写的 Agent 技能，教 AI 用 Obsidian CLI 与双链/白板/数据库等开放格式；② YishenTu/claudian 15.3k★——把 Claude Code/Codex 嵌进 Obsidian 侧边栏；③ breferrari/obsidian-mind 4.6k★——给 AI 编程助手装长期记忆的自组织笔记库。"
confidence: A
---

# GitHub热门精选 Vol.016：Obsidian AI 三件套

> [!abstract] 摘要
> 狐狸的 AI 情报站 Vol.016，一分钟盘点 3 个 "Obsidian + AI" 开源项目，主线是**让 AI 真正读懂并住进你的笔记库**：① Obsidian CEO 亲自写的 Agent 技能包，让 Claude Code/Codex 等认识双链、白板、Bases 数据库等开放格式；② 把 Claude Code 直接塞进 Obsidian 侧边栏，聊天/改稿/跑命令不切窗；③ 一个自组织笔记库模板，解决 AI 编程助手"记不住你"的问题，自动沉淀决策记录、本周战功，跨对话续接。

## 三个项目（star 数已实查 GitHub API 核实）

| # | 项目 | 作者 | 实查★ | 一句话 |
|---|---|---|---|---|
| ① | **obsidian-skills** | `kepano` | **48,328**（3,444 forks，MIT） | Obsidian CEO 亲写的 Agent 技能，教 AI 用 Obsidian CLI + 开放格式 |
| ② | **claudian** | `YishenTu` | **15,309**（1,022 forks，MIT） | 把 Claude Code/Codex 作为 AI 协作者嵌进 vault 侧边栏 |
| ③ | **obsidian-mind** | `breferrari` | **4,638**（534 forks，MIT） | 自组织笔记库，给 AI 编程助手提供持久记忆 |

> 视频标注 48,219 / 15,273 / 4,633，与我核查时（2026-09-15）几乎一致，三仓库均真实活跃（最近 push 在 2026-09-02 ~ 09-14），可信度高。

## ① obsidian-skills —— 教 AI 用 Obsidian（CEO 亲写）

- 仓库：https://github.com/kepano/obsidian-skills
- 官方描述：*Agent skills for Obsidian. Teach your agent to use Obsidian CLI and open formats including Markdown, Bases, JSON Canvas.*
- `kepano` 即 Obsidian 创始人/CEO Steph Ango，等于是官方下场给 AI Agent 写"教材"。
- 装进 Claude Code / Codex 等后，AI 就认识**双链、白板（Canvas）、数据库视图（Bases）**这些 Obsidian 开放格式，能读懂整个笔记库。
- 视频口播："Obsidian 的 CEO 亲手写了一套教材，装进 Claude Code，AI 就认识双链、白板、数据库视图这些开放格式，读懂你整个笔记库。"

## ② claudian —— 把 Claude Code 塞进侧边栏

- 仓库：https://github.com/YishenTu/claudian
- 官方描述：*An Obsidian plugin that embeds Claude Code/Codex as an AI collaborator in your vault.*
- Obsidian 插件，在侧边栏直接跑 Claude Code / Codex：**聊天、改稿、跑命令不用切窗口**。
- @ 点名库里的文件；选中一段文字让 AI 当面改，**改了哪个字都看得见**（diff 可见）。
- 视频提到"官方插件市场 208 万次安装"（此数字未独立核实，存疑待查——仓库 star 1.5 万，插件市场下载量与 star 不是一个口径，可能属实但需以 Obsidian 插件市场页面为准）。

## ③ obsidian-mind —— 笔记库当 AI 的长期记忆

- 仓库：https://github.com/breferrari/obsidian-mind
- 官方描述：*A self-organizing Obsidian vault that gives AI coding agents persistent memory. Claude Code, Codex CLI, Gemini CLI.*
- 针对痛点："AI 编程助手什么都好，就一个毛病——记不住你。"
- 提供一套**笔记库模板**给 AI 装上长期记忆：开完会跟它说两句，**会议纪要、决策记录、本周战功全替你写好**；下次对话接着上一次聊（跨会话上下文续接）。
- 支持 Claude Code、Codex CLI、Gemini CLI。

## 与本机/13BIT 体系的相关性

- [!] 三个项目都围绕 Obsidian——本机主库在 `~/.hermes/obsidian_vault/`，且已有官方 `obsidian` 技能。**① obsidian-skills 与现有技能高度互补**，可增强 agent 对双链/Canvas/Bases 的理解，最值得评估。
- [!] ③ obsidian-mind 的"跨会话持久记忆"与本机 Hermes MEMORY.md 机制、以及昨天装的 OMH `memory.provider` 属于同一命题，存在功能重叠，装前需想清楚用哪套，避免记忆后端打架。
- [ ] ② claudian 是 Obsidian 桌面插件（非 Hermes 技能），要装需在 Obsidian 应用内操作，属于 BOSS 个人使用层，未自动安装。

## 口播全文（Whisper 转录，含纠错标注）

> `【】` 内为根据画面/GitHub 核查纠正后的原词（Whisper 把 Obsidian/Claude/kepano 等专有词识别得较乱）。

一分钟带你了解热门开源项目。

【① obsidian-skills】
研究员开源【obsidian-skills】项目，
Obsidian 的 CEO【亲】手写了一套教材，
装进【Claude Code】，AI 就认识双链、白板、数据库【视图】这些开放格式，
读懂你整个笔记库。

【② claudian】
研究员开源【claudian】项目，
官方插件市场 208 万次安装。
他把【Claude Code】塞进 Obsidian 侧边栏，
聊天、改稿、跑命令不用切窗口。
打个【@】点名库里的文件，
选中一段字 AI 当面改，
改了哪个字都看得见。

【③ obsidian-mind】
研究员开源【obsidian-mind】项目。
AI 编程助手什么都好，就一个毛病——记不住你。
这个笔记库模板给它装上长期记忆，
开完会跟它说两句，
【会议】纪要、决策记录、本周战功全替你写好，
下次对话接着上一次聊。

还想了解哪类工具，评论区留言，下期更新；
关注我，为你推送热门 GitHub 项目。

## 关键画面

![[76853951【手机号】-f_01.png]]
**f_01（开场）**：本期总览卡 Vol.016 / 03 PROJECTS——① obsidian-skills 教AI用Obsidian 48,219 ② claudian AI住进笔记侧边栏 15,273 ③ obsidian-mind 笔记库当AI的记忆 4,633。

![[76853951【手机号】-f_02.png]]
**f_02（项目1）**：`kepano/obsidian-skills` 仓库页，48,219★，旁白"Obsidian 的 CEO 亲手写了一套教材"。

![[76853951【手机号】-f_03.png]]
**f_03（项目1）**：README 与安装说明，可见 Marketplace / `obsidian-skills` 安装命令，旁白讲 AI 认识双链/白板/数据库视图。

![[76853951【手机号】-f_04.png]]
**f_04（项目2）**：`YishenTu/claudian` 仓库页，15,273★，"把 Claude Code 塞进侧边栏，官方插件市场 208 万次安装"。

![[76853951【手机号】-f_05.png]]
**f_05（项目2）**：claudian README 内 prompt 结构化示例，旁白"聊天、改稿、跑命令不用切窗口"。

![[76853951【手机号】-f_06.png]]
**f_06（项目2）**：同一仓库页，旁白"改了哪个字都看得见"。

![[76853951【手机号】-f_07.png]]
**f_07（项目3）**：`breferrari/obsidian-mind` 仓库页，4,633★，可见 North Star / Weekly / Active Projects 等模板说明，旁白"每次对话都接着上一次，就一个毛病记不住你"。

![[76853951【手机号】-f_08.png]]
**f_08（项目3）**：Claude 对话截图（Interval notes / people / Review Goals），旁白"纪要、决策记录、本周战功全替你写好"。

![[76853951【手机号】-f_09.png]]
**f_09（结尾）**：obsidian-mind 对话捕获示例（EA/type/context、interval notes、people/），引导评论区留言 + 关注。

## 行动项

- [x] 三仓库真实性 + star 数已用 GitHub API 核实（全部真实、活跃、MIT）。
- [ ] 待 BOSS 决定是否评估 **① obsidian-skills**（与本机 obsidian 技能互补，价值最高）；注意 ③ 与 OMH/Hermes 记忆机制有重叠，不宜盲装。
- [ ] ② claudian 属 Obsidian 桌面插件，需在 Obsidian 应用内安装，非 agent 侧动作。

## 来源

- 抖音链接：https://v.douyin.com/LJRvE2b1hrQ/
- 作者：狐狸的 AI 情报站（Vol.016）
- 视频 ID：76853951【手机号】
- 抓取时间：2026-09-15
- 核查：https://github.com/kepano/obsidian-skills · https://github.com/YishenTu/claudian · https://github.com/breferrari/obsidian-mind
- 素材：`~/WorkBuddy/douyin-tmp/dy-3M4Alb/`（mp3 / mp4 / whisper txt / 9 帧）
