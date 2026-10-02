---
name: video-ingest-to-obsidian
description: 抖音/B站视频真实转录并入库 Obsidian 知识库。
version: 1.0.0
author: 小卡 (Hermes)
license: MIT
metadata:
  hermes:
    tags: [视频入库, 抖音, B站, 转录, Obsidian, 知识库]
    related_skills: [obsidian, xiaoka-boss-ops]
---

# 短视频入库管线（抖音 / B站 → 共享 Obsidian）

把 BOSS 发来的短视频链接变成共享库里一篇可溯源的笔记。核心纪律：**转录必须真实，提炼必须能溯源**。

## When to Use
- BOSS 发来 `v.douyin.com` / `douyin.com` / `b23.tv` / `bilibili.com` 链接或 BV 号
- 「入库」「存知识库」「这条视频学一下」「批量抓视频」类指令
- 要把某个账号近期作品批量沉淀进库

**Don't use for:** 只想要链接解析/无水印直链（用共享库 `video-downloader`）；纯图文小红书（非本管线覆盖）。

## 铁律（违反即作废）
1. **转录稿必须由真实 ASR 从音视频生成**，禁止 LLM 凭空生成口播稿。
   判据：每一句要点都要能在转录稿里指出出处原句或时间点；指不出的就删，不要软化成「大概意思是」。
2. **目录固定**，全公司共用一套，落错目录等于没共享：
   | 内容 | 目录（相对 vault 根） |
   |---|---|
   | 抖音 | `08-抖音视频学习/` |
   | B站 | `07-B站视频学习/` |
3. **文件名用连字符、无空格** —— Obsidian wikilink 遇空格需转义，会造成链接断裂。
4. **失败就报失败**：下载不到 / 转录空 / 账号需登录 → 如实说明卡在哪一步，不要用笔记格式把空壳糊进库。

## Procedure

### 0. 预检（不可跳过）
共享库里的入库技能是在**别的机器**上写的，脚本路径可能在本机不存在。
**先跑预检，再向 BOSS 承诺能入库**：
```bash
python3 <本skill目录>/scripts/preflight.py
```
它会列出 ffmpeg / 下载器 / 转录后端 / NAS 技能 / 登录态各自的实际状态。
**判据**：转录后端与下载器必须同时可用，缺任一项就先补齐或先问 BOSS，不要边做边发现。

### 1. 判断形态
视频 / 图文（图文走截图+视觉提炼，不进转录流程）；确认是单条还是批量。

### 2. 下载
- **单条** → 共享库 `video-downloader`（第三方解析 API，不依赖登录态）
- **批量账号作品** → 共享库 `douyin-video-downloader`
- 裸 `yt-dlp` 直连抖音会命中 412 风控；抖音优先走上面两个已处理登录态的技能
- 落地目录 `<scratch>/<slug>/`

### 3. 转录
音频抽出来跑本地 ASR（faster-whisper / SenseVoice 之类，中文模型）。
**转录返回空或置信度低 → 停下报告，不要进入提炼。**

### 4. 提炼
只读真实转录稿，产出：标题、3~8 条要点（每条带原句/时间点）、可执行 takeaway、关联已有笔记、标签。
拿不准的标「待核实」；画面类信息用 `ffmpeg -ss <秒> -vframes 1` 截帧核对，不臆测。

### 5. 写库
YAML frontmatter + 正文，用 `write_file`；写 NAS 受安全根限制时先写本地再 `cp`（见 `xiaoka-boss-ops`）。
```yaml
---
title: "<标题>"
source_url: "<原链接>"
platform: douyin          # 或 bilibili
提炼日期: YYYY-MM-DD
tags: [提炼, 抖音, <领域>]
added_by: <执行者>
summary: "<一句话摘要>"
---
```
图片进 `attachments/` 并用 `![[xx.png]]` 引用。目标目录若有 `index.md` 则追加一条。

## Pitfalls
- **同名下载器有两个**，语义相反：单条入库用 `video-downloader`；只有明确说「批量/拉某账号全部作品」才用 `douyin-video-downloader`。选错会静默拉到无关内容。
- **登录态**：抖音游客态（仅 ttwid）下载会报 `Fresh cookies needed`，需要 `sessionid`/`sid_tt`。这是账号授权前提，不是工具故障——走扫码登录拿持久 profile，别去猜凭据。
- **知识星球类接口限流**会在同族管线里出现（`code 1007`/`1059`）。限流时别硬刷，换时间重试，并在笔记里标注「附件未入库 + 原链接」，不留空壳。
- **共享库技能重名会让我加载失败**：新建技能前 `ls <共享库> | grep -i <name>` 查重，撞名就换名。

## 知识资产位置
前序 agent 的交接笔记与链路文档在 vault 里（内含铁律出处、账号限流史、目录规范），读它们比重新踩坑快。
索引见 `references/knowledge-assets.md`。

## Verification
- 笔记 `source_url` 真实可点，且要点能在转录稿里逐条溯源
- 文件落在正确目录、文件名无空格、frontmatter 完整、带 `提炼` 标签
- 图片 wikilink 能打开
- 目标目录 `index.md` 已追加
