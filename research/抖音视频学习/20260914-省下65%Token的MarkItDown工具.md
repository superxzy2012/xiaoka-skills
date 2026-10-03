---
title: "你原本可以省下65%的Token，但你不用这招（MarkItDown）"
source: "https://v.douyin.com/ncMbooaF7Tw/"
platform: douyin
type: video
author: "Sunmy教你玩AI"
video_id: "76775080【手机号】"
published: 2026-09-14
captured: 2026-09-14
tags: [douyin, 提炼, MarkItDown, Token优化, AI工具, codex, github]
summary: "把任意格式文件（PDF/Office/音频/视频）先用微软开源工具 MarkItDown 转成 Markdown 再喂给 AI，剥离图片与版式杂质、只留干净结构，Token 消耗大幅下降且输出质量更高——因为 Markdown 是大模型的『母语』。"
confidence: A
---

# 你原本可以省下65%的Token，但你不用这招

> [!abstract] 摘要
> 博主 Sunmy 指出一个大多数人忽略的浪费：把 PDF / Word 等文件**直接上传**给 AI，一开口就烧掉上万 Token——因为 AI 要同时处理文字、图片、版式、表格。解法是先用微软开源的 **MarkItDown**（GitHub 17.6 万 stars）把文件转成 Markdown 再喂给模型，一行命令省掉一大半 Token，而且因为只剩"最干净最有效"的部分，AI 输出质量反而更好。底层原因：GPT / Claude / Codex 等主流大模型的训练语料里充满海量 Markdown 文本，Markdown 相当于它们的"母语"。

## 要点

1. **痛点**：直接上传 PDF 给 AI，发出第一个指令就消耗掉上万 Token；AI 被迫同时解析文字、图片、版式、表格四类信息。
2. **工具**：`MarkItDown`——微软开箱即用的开源工具，GitHub 17.6 万 stars，一行命令把任意格式转成 Markdown。
3. **支持格式**：PDF、PPT、Word、Excel、**音频、视频**（音频/视频会走语音转写）。
4. **核心收益**：剥离图片、样式、排版、碎表格等"废料"，只保留"干净最有结构的部分"，Token 节省一大半。
5. **质量收益**：Token 少了不是唯一好处——去掉噪音后 AI 输出的效果和质量会更好（Less noise, more signal）。
6. **为什么是 Markdown**：GPT / Claude / Codex 等主流大模型训练数据里有海量 Markdown 文本，Markdown 等同于它们的"母语"，模型看到后"不会迟疑、更加能理解"。
7. **一句话用法**：`markitdown input.file > output.md`。

## 本机实测验证（2026-09-14，小豆实跑）

> [!success] 已在 BOSS 本机安装并验证
> - 安装：`/Users/【BOSS英文名】/.workbuddy/binaries/python/versions/3.13.12/bin/python3 -m pip install "markitdown[all]"`（清华镜像）
> - 版本：`markitdown 0.1.7`，`from markitdown import MarkItDown` 导入成功
> - 实测通过的格式：**HTML / PDF / DOCX**（均输出正确 Markdown，表格、标题层级保留）

**Token 实测对比**（样本：`用WorkBuddy打造视频号OBS直播间.pdf`，11 页，含 3 张内嵌图）

| 喂法 | 估算 Token | 相对成本 |
|---|---|---|
| 整页渲染成图片喂视觉模型 | ~68,454 | 基准 100% |
| PDF 文字层直接抽文本 | ~3,193 | 4.7% |
| **MarkItDown 转 Markdown** | ~3,389 | 5.0% |

结论修正：MarkItDown 的真实省 Token 场景是**"本来要连图一起喂"**的时候——相比图像方式省 **95%**，与视频"省 65%"的说法方向一致。但对于**纯文字型 PDF**，它的 token 量与直接抽文本基本持平（本例还多 6%，因为补了标题/表格结构）——此时它的价值在**结构保留与格式统一**，而不在省 Token。

## 口播全文（Whisper 转录，含人工纠错标注）

> 转写模型对专有名词有误识别，`【】` 内为纠正后的原词。

如果你还是直接把文件上传给【AI】，
当你发出第一个指令的时候，
它就会消耗掉上万 Token。
AI 每次处理类似于 PDF 这样的文件，
它要看文字，
它要处理图片、
【版式】格式以及表格。
现在这个微软开箱【即用】的工具，
【MarkItDown】在【GitHub】上已经有了 17.6 万的【stars】。
它可以把任意格式 PDF、【PPT】、Word、Excel、
音频或者是视频，
【通过】一行命令
【转换】成【Markdown】格式。
那 Token 节省的就是一大半。
它【提取的是文】档里面最干净最有效的部分。
【去掉】这些废料之后，
AI 输出的效果质量会更好。
那么为什么是【Markdown】格式呢？
因为目前所有的主流大模型，
【GPT】、【Claude】、
训练数据里面都有海量的【Markdown】文本。
【Markdown】文本就相当于是它们的母语。
它看到这些信息不会迟疑，
也更加能理解。
更多类似有用的 AI 信息，
点点关注，
关注看更多。

## 关键画面

![[76775080【手机号】-f_01.png]]
**f_01（00:00-00:05）**：开场——`AI FILE INPUT / 上传文件 / READY`，`PDF DROP FILE HERE`，右侧柱状图：`TOKEN COST BEFORE FIRST PROMPT 1,220 / 10K / 20K / 30K / 35K` → 直指"第一个指令就烧上万 Token"。

![[76775080【手机号】-f_02.png]]
**f_02（00:05-00:10）**：`WHAT AI SEES 不只是文字`——列示 AI 实际要处理的东西：文字、图片、PDF。

![[76775080【手机号】-f_03.png]]
**f_03（00:10-00:15）**：GitHub 仓库页面截图，简介 `用于将文件和办公文档转 Markdown 的 Python 开源工具`；可见 `57.1(k stars) / 12.9k` 等仓库指标。

![[76775080【手机号】-f_04.png]]
**f_04（00:15-00:20）**：`ONE COMMAND · MANY FORMATS 任意文件，统一变干净`——图标列：`PDF / DOCX / XLSX / PPTX / MP3 / VIDEO`。

![[76775080【手机号】-f_05.png]]
**f_05（00:20-00:25）**：终端演示 `$ markitdown input.file > output.md`，输出 `.md` 含 `# Title / - clean list / |table|`。

![[76775080【手机号】-f_06.png]]
**f_06（00:25-00:30）**：`LESS NOISE · MORE SIGNAL  Token 减半，结构留下`——原文件 100%（图片样式、排版、碎表格）→ Markdown 48%（只保留重要结构）。

![[76775080【手机号】-f_07.png]]
**f_07（00:30-00:35）**：`WHY MARKDOWN？ 为什么偏偏是 Markdown？`——列 `GPT / CLAUDE` 等模型 logo。

![[76775080【手机号】-f_08.png]]
**f_08（00:35-00:40）**：`Markdown = AI 的母语`——`"code" / |table| / #heading / - list item`，旁白"相当于是它们的母语"。

![[76775080【手机号】-f_09.png]]
**f_09（00:40-00:43）**：结尾 `点点关注`。

## 行动项 / 已落地

- [x] 本机安装 `markitdown[all]`（v0.1.7），PDF/DOCX/HTML 实测通过
- [x] 入库技能已存在：`~/.hermes/skills/markitdown-skill`（本次补记本机真实安装路径与 Python 解释器）
- [ ] 待评估：把 markitdown 接入日常文档入库管线，替代"只抽文字层"，统一输出为 Markdown

## 来源

- 抖音链接：https://v.douyin.com/ncMbooaF7Tw/
- 作者：Sunmy教你玩AI
- 视频 ID：76775080【手机号】
- 抓取时间：2026-09-14
- 素材：`~/WorkBuddy/douyin-tmp/dy-IZrW2P/`（mp3 / mp4 / whisper txt / 9 帧）
