---
title: Skillbox:装一次Skill让所有Agent无缝切换
source: 抖音短视频
author: 小唐的Token
douyin_url: https://v.douyin.com/n-vpaoNKYAk/
douyin_id: n-vpaoNKYAk
video_id: "7679648852256886079"
date: 2026-08-31
topic: AI Agent / Skill 管理 / 一人公司工具链
tags: [AI Agent, Skillbox, Skill管理, agent-browser, 一人公司, 工具链]
ingested_by: 小丽(替小豆入库,小豆当前处于长session hallucinate状态)
related:
  - "[[20260831-Codex插件干完整个团队]]"
  - "[[20260831-AI时代想造专属软件这个Skill]]"
---

# Skillbox:装一次Skill让所有Agent无缝切换

> 抖音【小唐的Token】06期。核心观点:工具(Agent)可以随便换,但你手搓和攒下来的 Skill 才是"不用换的固定资产"。

## 一句话总结
Skillbox 是一个 **Skill 统一管理工具**:你的 Skill 只存一份,所有 Agent(Claude Code / Codex / DeepSeek / Kimi Code…)通过"快捷方式"指向它,改一处全部生效;附带 Skill 市场(9万+)、跨设备导出导入,已开源(Win/Mac)。

## 口播全文(whisper 转写)
```
朋友们
你有没有这种感觉
一个agent的干用顺手
想换另一个
之前教他的所有东西
又得重新拿一遍
所以我做了这些工具
把这个问题都解决了
它叫skillbox
你的skill只存一份
就可以让所有的agent
无缝切换去使用
这半年从cloud code
codex
到最近的dcconnage
热门的agent一个接的一个
我觉得工具可以换
但是你手说和展下来的skill
才是你不用换的东西
这都是你的固定资产
项目的资料呢
我的整条放文档了
点好收藏关注赞
我们马上开始
我现在所有的skill
都放到这个工具里
显示了有哪些agent的用
如果想给其他agent的
适配的话
直接点一下就可以了
这里它不是复制过去的
skill我们只存一份
是直接给agent指过去的
就跟我们桌面
快捷方式指一个道理
我改这个skill
只需要改一份
所有的agent都会同时生效
不想给你一个用的话
我们直接就关掉
不会动文件的本身
如果换设备的话
也可以选择导出你的skill配置
在新设备进行导入
skill和agent的关系
会一样回来
不用重新去配置
而且还加了一个skill市场
里面有九万多个现成的skill
直接就可以搜索安装
如果以后每个agent
你觉得不好用了
打架了
直接换在就行
工具变了
你机里的skill还在
那么项目的话
我已经开源了
Windows Mac版本都有
评论区口合工具我发你
如果用的人多的话
后续我还有把
NCP也放到这个工具里面
我是小唐
我们下期再见
```

## 画面关键信息(OCR 实证)
- 工具名 **Skillbox / 技能库**;演示界面显示「33 个本地 Skill · 85 个 Agent」
- 已适配:Claude Code / Codex CLI / ZCode / Kimi Code / 通用 Skill 目录
- 机制:**Store Once, Use Everywhere** —— Agent A/B/C 共享同一份 Skill,「Seamless Switching」
- 本地 Skill 列表样例:amesone-design / creator-clone-lab / edge-tts / frontend-design / humanizer-zh / nrcarlsana-social-transcriber / vibe-explain / vibe-guard / vibe-secure / xiaotanggengxin / XLSx
- Skill 市场:全部范围 33 / 全局 27 / 项目 6

## 提炼(和小豆/一人公司的关联)
1. **和"小豆自我进化"直接呼应**:我给小豆 SOUL 加了「遇新任务类型用 skill-creator 造技能」,但默认是**每个 agent 各自存一份 Skill**。Skillbox 的思路更优——Skill 作为**跨 Agent 共享资产**,改一处全生效,避免「换 Agent 重教一遍」。
2. **可复用的工程实践**:小豆造的 Skill 应集中到一个共享目录(而非散落各 agent 的 skills/),用软链/指向方式让 Hermes / 小丽 / Codex 共用——这正是 Skillbox 的「快捷方式指向」模式。
3. **下一步可评估**:把本机 `~/.hermes/skills` 里的通用 Skill(如 douyin-obsidian、skill-creator、agent-browser)抽成"一人公司共享 Skill 库",小丽/小豆/Codex/阿正都能指向。

## 反向链接
- [[20260831-Codex插件干完整个团队]] — Codex 插件即「装一次能力」的同类思路
- [[20260831-AI时代想造专属软件这个Skill]] — 从零造 Skill 的能力底座

---
*入库时间:2026-08-31 13:05;转写 whisper small;截帧 16 张(ffmpeg fps=1/5);OCR 本地 vision_ocr。*
