---
title: "八大开源 GitHub 自动视频生成：一条 prompt 出整片"
source_url: "https://v.douyin.com/_ht74WmUs64/"
douyin_id: "7693747954594762022"
platform: douyin
作者: "学霸妈妈讲AI"
入库日期: 2026-10-09
时长: "00:34"
tags: [提炼, 抖音, 开源, AI视频生成, MoneyPrinterTurbo, VoiceStudio, Wan2.2, ComfyUI, HyperFrames, Manim, OpenCut, FasterWhisper, 自动化流水线]
added_by: 小豆
置信度: A
summary: "8 个开源项目串成一条「prompt → 成片」全自动流水线：脚本(MoneyPrinterTurbo)→声音克隆(VoiceStudio)→文生视频(Wan2.2+ComfyUI)→代码帧(HyperFrames+Manim)→剪辑(OpenCut)→字幕(Faster-Whisper)，合计 553,454 stars，全部 15 天内有提交（数据核对于 2026-10-06）。"
---

# 八大开源 GitHub 自动视频生成 — 一条 prompt 出整片

## 一句话结论

不用任何商业工具，8 个开源项目按流水线串起来：**给一行 prompt，自动完成脚本→配音→素材→代码帧→剪辑→字幕，直接出成片**。

## 八项目流水线（截帧 OCR 逐项核对，数据核对时间 2026-10-06 02:19 UTC）

| 步 | 工序 | 项目 | Stars | 许可证 / 版本 | 最近 push | 干什么 |
|---|---|---|---|---|---|---|
| 1 | 脚本+成片框架 | **MoneyPrinterTurbo** | 128,661 | MIT · v1.3.8 | 2026-10-04 | 给主题/关键词 → 自动写脚本、配素材、做字幕配乐、出视频 |
| 2 | 声音 | **VoiceStudio** | 53,806 | AGPL-3.0 · v0.5.6 | 2026-10-05 | 本地声音克隆+配音+转写+有声书，宣称 646 种语言全本地 |
| 3 | 文生视频 | **Wan2.2** | 17,742 | Apache-2.0 · 无 release tag | 2026-09-21 | 开源 T2V / I2V / TI2V 模型，5B 模型需 ≥24GB 显存 |
| 4 | 视频节点图 | **ComfyUI** | 136,222 | GPL-3.0 · v0.39.0 | 2026-10-06 | 图像/视频/音频模型的可视化节点图引擎，8 个里 star 最高 |
| 5 | 代码帧 | **HyperFrames** | 57,356 | Apache-2.0 · v0.8.135 | 2026-10-06 | HTML+计时属性 → headless Chrome 确定性渲染成 MP4 |
| 6 | 数学动画 | **Manim** | 41,295 | MIT · v0.21.0 | 2026-10-05 | Python 代码生成讲解型动画（3Blue1Brown 同款引擎） |
| 7 | 剪辑 | **OpenCut** | 92,654 | MIT · v0.3.0 | 2026-09-24 | 免费开源时间线视频编辑器 |
| 8 | 字幕 | **Faster-Whisper** | 25,718 | MIT · v1.2.1 | 2026-10-05 | 语音时间戳转写字幕，宣称比原版 Whisper 快至 4 倍、更省内存 |

合计 **553,454 stars**；许可证构成：4×MIT + 2×Apache-2.0 + 1×GPL-3.0 + 1×AGPL-3.0；核对时 8 个项目全部在 15 天内有 push。

## 已知限制（视频画面原样标注）

- 声音克隆需要**声音所有者本人许可**（VoiceStudio README）
- Wan2.2 大模型需要 **24GB+ 显存**
- GPL-3.0 / AGPL-3.0 两个项目商用组合时注意许可证传染性

## 与我们现有体系的关系（我的判断）

- 我们已有 **MoneyPrinterTurbo 同类能力雏形**：小豆抖音管线（yt-dlp → whisper → ffmpeg → obsidian）就是它的"逆过程"（视频→知识）；正向生成（prompt→视频）可直接复用 whisper/ffmpeg 两件套。
- **Faster-Whisper 可直接替换现有 whisper CLI**：我们现在用 openai-whisper small（CPU 慢），Faster-Whisper 宣称快 4 倍更省内存，且同为 MIT。
- ComfyUI 我们**已装**（creative/comfyui 技能在册）；Wan2.2 模型文件大、需 24GB 显存，本机 M 系列芯片跑 5B 需量化方案，暂不动。

## 入库执行记录（"入库，找到并安装视频里提到的"）

| 项目 | 真实仓库（已核实） | 状态 |
|---|---|---|
| MoneyPrinterTurbo | `harry0703/MoneyPrinterTurbo` | ✅ 已克隆 348MB（含 Docker/配置） |
| VoiceStudio | `debpalash/VoiceStudio` | ✅ 已克隆 123MB |
| Wan2.2 | `Wan-Video/Wan2.2` | ✅ 已克隆 18MB；模型 24GB+ 显存，本机只存代码与脚本，不下模型 |
| ComfyUI | `comfyanonymous/ComfyUI` + `ltdrdata/ComfyUI-Manager` | ✅ 本体+依赖已装，**服务已起** v0.39.0 @ http://127.0.0.1:8188（MPS，实测 200） |
| HyperFrames | 官方源 `heygen-com/hyperframes`（GitHub 组织 `hyperframes`） | ✅ 已克隆（README 已确认功能=HTML+计时属性→headless 渲染 MP4） |
| Manim | `ManimCommunity/manim` | ✅ pip 安装 **v0.22.0**，实测渲染 Hello.mp4 成功 |
| OpenCut | `OpenCut-app/OpenCut` | ✅ 已克隆 1.4MB |
| Faster-Whisper | `SYSTRAN/faster-whisper` | ✅ pip 安装 **v1.2.1**，实测转写本视频成功 |

所有仓库统一放在 `/Users/【BOSS英文名】/.hermes/knowledge/`。访问 GitHub 需走本机代理 `http://127.0.0.1:7897`（直连超时）。

## 完整口播转写（原文，34 秒）

<details>
<summary>点击展开</summary>

以为做短视频还在苦苦熬夜剪辑
赶紧停下
你以为的技术壁垒已经被彻底撕碎
全球开源社区暗藏的55万star黑科技矩剑曝光
只要给它一航prompt
八大顶级ai项目瞬间在云端自主狂标
从脚本合成云样北摄音客龙
到24级显存强行拉满高帧率渲染
甚至用Python代码直接编译实量动画
不需要人工插手
从造成故障到极其画质一期合成
别再用传统模式打雷耗战了
这套将为打击时的工具链
正在悄悄宠够未来的内容生长割局

</details>

> 转写噪声说明：whisper 对 fast-talking 中文识别质量差（"黑科技矩剑"应为"黑科技矩阵"、"云样北摄音客龙"应为"零样本声音克隆"），关键数字与项目名以截帧 OCR 为准，口播仅作背景。

## 附件

- 视频原始文件：`~/WorkBuddy/douyin-tmp/7693747954594762022/video.mp4`（2.05 MB，00:34）
- 截帧 11 张：`~/.hermes/obsidian_vault/attachments/20261009-7693747954594762022/`
- 转写源文件：`~/WorkBuddy/douyin-tmp/7693747954594762022/video.txt`