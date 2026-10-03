# V7 零 Token 使用 Hermes 生成图片和视频

> **作者**：叶秋大大
> **来源**：https://v.douyin.com/7-nCb_0p3ck/
> **采集日期**：2026-08-10
> **转录引擎**：SenseVoice-Small | 视频时长 ~80 秒
> **质量评分**：⭐ 1/5（**只演示了"看，能生图"，无技术细节**）

---

## 视频原方案

> 用 SKILL.md（通用技能文件）让 Hermes 零 token 生成图片和视频

---

## 视频提到的关键点

1. **大语言模型** = 走"网页大模型转 API"工具（前面 V3 讲过）
2. **生图/生视频** = 走 **SKILL.md**（**因为是 SKILL.md 文件**）
3. **SKILL.md 通用性**：
   - Hermes Agent
   - 龙虾（OpenClaw）
   - Claude Code
   - Codex
4. **演示**：让 Hermes 查美股昨日收盘 → 自动写生图提示词 → 浏览器自动化注入微博/微信 → 生成图片保存桌面

---

## ⚠️ 视频没说清楚的关键点

| 缺口 | 影响 |
|---|---|
| **没贴 SKILL.md 的内容** | 核心是 SKILL.md，但**完全没贴** |
| **没贴"生图 skill"具体长什么样** | 无法复现 |
| **没贴提示词注入的实现** | 浏览器自动化部分模糊 |
| **没说用哪个生图工具** | ComfyUI？SD？还是别的？ |

---

## 💡 真实可复用部分

**概念有价值**：

1. **SKILL.md 是跨 agent 通用格式**（Hermes/OpenClaw/Claude Code/Codex）—— 这点 **你已有 skills 系统验证过**（你 53 个 skills 全是 SKILL.md）
2. **生图/生视频这类"非文本任务"**很适合用 SKILL 沉淀（因为是**流程化**操作）
3. **"提示词注入到外部网站"** 是浏览器自动化 + AI 的典型组合用法

---

## 🎯 对你现有的潜在价值

**完全对应你的现状**：

| 你现在有的 | 视频讲的 |
|---|---|
| 53 个 SKILL.md | "SKILL.md 通用" |
| Hermes skills 系统 | "用在 Hermes Agent" |
| 飞书 13 bot | 演示用了"微博/微信"——**你本可以用飞书** |
| oMLX（已暂停）| 视频提到"本地模型调用"——你**有但暂停了** |

**唯一缺**：**生图生视频的 SKILL.md 本身**。

**后续行动**：
- 如果你要给 13 bot 加"日报可视化"功能，可以照这个思路写个生图 SKILL
- ComfyUI 是当前主流——视频没说用啥，**但你 hermes-home/skills/creative/touchdesigner-mcp** 提示有 MCP 路线

---

## 📎 原始记录

- 视频：https://v.douyin.com/7-nCb_0p3ck/
- Raw：`~/跨境电商/知识库/raw_docs/零Token使用hermes生成图片和视频 深入研究skill技能通用技能可以用在HermesAge.md`
- 转录字数：1720 字
- 跑通耗时：7 秒
