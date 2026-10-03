# V8 Cherry Studio 自定义 API 实现零 Token 调用大模型

> **作者**：叶秋大大
> **来源**：https://v.douyin.com/CMlecSq7FWg/
> **采集日期**：2026-08-10
> **转录引擎**：whisper-small | 视频时长 ~169 秒
> **质量评分**：⭐ 4/5（**有完整可复现路径 + 实操演示**，最贴近你 0-token 需求的一期）

---

## 核心思路（口播 + 画面）

> 用 **Cherry Studio** 客户端的「自定义 API / 自定义提供商」功能，把**免费网页端的大模型**（硅基流动、Kimi 等）伪装成 **OpenAI 兼容 API**，实现零 Token 调用。

关键认知（画面印证）：Cherry Studio 自带几十家内置提供商（Fireworks / 英伟达 / Grok / Hyperbolic / Mistral / Jina / Perplexity / ModelScope / 腾讯混元 / 百度千帆 / GPUStack / Qwen / Voyage AI / AWS Bedrock / MiniMax / Groq / Together / DeepSeek / Kimi…），但要用「零 Token」的免费模型，必须走**自定义 API**。

---

## 视频操作步骤（口播整理，已纠正 ASR 音译）

1. 打开 **Cherry Studio → 设置 → 添加供应商**
2. 选 **OpenAI**（因为要接入的自定义服务都兼容 OpenAI 格式）
3. 提供商名字**任意取**（反正都是零 Token 的免费服务）
4. 下拉选 **「自定义 API」**（不是内置列表）
5. 登入你的 **API 控制台**（如硅基流动 / SiliconFlow）→ 复制 **Base URL** 与 **API Key**
6. 把 **Base URL** 填到「API 地址」栏 → 添加
7. 把 **API Key** 粘贴到「API 密钥」栏
8. 选模型（视频演示用 **Kimi**，口播称 K3）→ 点「获取列表」
9. 点「检验测试」→ 连接成功 ✅
10. 现在能看到**零 Token 大模型列表**，每个模型标注支持的功能（工具 / 推理 / 视觉）
11. 回到 Cherry Studio 主界面 → 进**智能体**，内置工具已默认开启，能调用**知识库 / MCP / 技能**
12. 还可添加一个**免费嵌入式模型**（用于后续建知识库的向量化）
13. **演示**：用 Kimi 在本地桌面**新建 TXT 文件** → 成功；再让它**分析一份 A股大盘分析文档**并把总结写入该 TXT → 成功，结构清晰

---

## ASR 音译纠错表（whisper 识别错的词已还原）

| 转写原词 | 正确含义 |
|---|---|
| AVS扣端 | API 控制台 |
| AVI KING | API Key |
| BassUrAir | Base URL |
| Carrie Studio | Cherry Studio |
| Kimi K3 | Kimi（视频口播称 K3） |
| 规矩流动 | 硅基流动（SiliconFlow） |
| 正能体 | 智能体 |
| 支持库 | 知识库 |
| 揭漏 | 接入 / 调用 |

---

## ⚠️ 视频没说清楚的关键点

| 缺口 | 影响 |
|---|---|
| **Base URL 具体填什么值**（如硅基流动的 `https://api.siliconflow.cn/v1`）| 首次配要自己查 |
| **API Key 去哪领**（各平台控制台）| 需自行注册 |

---

## 💡 真实可复用部分

**这套方法 = 你「0 token 接入 WorkBuddy」的标准范式**：

1. **工具链同构**：Cherry Studio、Hermes、WorkBuddy 都是 OpenAI 兼容客户端，都支持「自定义提供商 + base_url + API key」。V3 已印证 Hermes 有「自定义入 API 方式」，WorkBuddy 同构可复用。
2. **真正零成本来源**：免费网页端大模型（硅基流动 / 智谱 / Kimi 等）的 API 额度 → 经「网页大模型转 API」工具反代为 OpenAI 兼容接口 → 客户端调用。

---

## 🎯 对你（OPC 一人公司 / Hermes / 13 bot）的实际价值

**高**。这是你最初想搞的「0 token 方法」的**客户端落地形态**：

| 你现状 | 视频给的扩展 |
|---|---|
| 火山方舟 Coding Plan（deepseek-v4-flash）作主力 | 加一层免费网页端模型作兜底（经 WorkBuddy 接入），封了也不慌 |
| 13 bot 实时调模型（有 token 成本）| 高频重复任务可切到 WorkBuddy 接的免费网页端模型，0 token |
| WorkBuddy 自定义 API（同构于 Hermes，V3 已印证）| 直接把硅基流动 / Kimi 的免费额度挂上去 |

**下一步建议**：先确认 WorkBuddy 的「自定义 API」字段名（V3 说视频没贴清楚），把硅基流动的免费额度接进去做最小验证。

---

## 📎 原始记录

- 视频：https://v.douyin.com/CMlecSq7FWg/
- 本地素材：`/Volumes/D/douyin-tmp/CMlecSq7FWg/`（video_unknown.mp4 + 8 帧 + whisper 转写 txt/vtt/srt/json）
- 转录字数：约 1100 字（whisper-small）
- 转录耗时：约 2 分钟（含模型下载）
