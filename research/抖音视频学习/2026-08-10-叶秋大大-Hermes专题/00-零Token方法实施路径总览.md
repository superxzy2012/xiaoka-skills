---
title: "00-零Token方法实施路径总览（yeqiudada系列融合）"
author: "小丽整理（融合 V8–V36）"
source: "抖音 yeqiudada（叶秋大大）29 条视频"
platform: "抖音"
date: "2026-08-10"
tags: ["零Token", "总览", "实施路径", "网页大模型转API", "WorkBuddy", "Hermes", "OPC", "跨境电商", "提炼", "地图"]
quality: "★★★★★"
---

> **本篇定位**：把 yeqiudada（叶秋大大）29 条「零 Token 使用 AI」视频融合成一张实施地图。先看本篇，再按索引跳读分篇。
> **核心目标**：把**免费网页端大模型**（智谱 GLM / Kimi / DeepSeek / 豆包等）转换成**标准 OpenAI 兼容 API**，接入 WorkBuddy / Hermes 这类客户端，**全程零 Token 成本**。

---

## 一、两条零 Token 路线（来自 V36）

| | 路线 A：OpenClaw（龙虾） | 路线 B：网页大模型转 API（推荐走这条） |
|---|---|---|
| 形态 | 重写的 AI Engine（TypeScript 重写） | 通用协议转换工具 |
| 原理 | 保存网页端登录 Cookie，调用时免认证 | 把外部端协议转成 OpenAI 标准 API |
| 适用 | 直接用现成 Engine | 接任意 OpenAI 兼容客户端 |
| 工具调用 | XML 模拟标签 | 加 Flex 网关支持多客户端并发 |
| 优势 | 已适配网页模型，写 Skill.md 即可 | **不绑定某客户端**，可接 Hermes / WorkBuddy / Cloud Code |

**结论**：你的路线是 **B**——免费网页模型经「网页大模型转 API」转标准 API，挂进 WorkBuddy 自定义 API。

---

## 二、标准接入步骤（以智谱 GLM 为例，融合 V21/V23，映射到 WorkBuddy）

1. 准备一个「网页大模型转 API」工具（OpenClaw 或同类），确保它能把 GLM / Kimi / DeepSeek 转成标准 OpenAI API
2. 在该工具里登录网页端并生成 **Base URL + API Key + 模型名（model ID）**
3. 打开 WorkBuddy → 自定义 API / 自定义提供商 → 填入：
   - **Base URL** = 本地网关地址
   - **API Key** = 复制来的 Key
   - **模型名** = 选中的 model ID
4. 开启**多轮上下文**（最大消息数 / 最大 Token 数 / 历史摘要），避免免费模型「健忘」
5. 若要做**工具调用**：用 **XML 格式**注入提示词（比 JSON 稳定，不易被模型破坏），打开解析开关（见 V22 / V24）

---

## 三、工具清单（按出现频次）

- **网页大模型转 API 工具**：核心底座，把所有免费网页模型转标准 API（V10/V12/V13/V15/V21/V23）
- **OpenClaw（龙虾）**：路线 A 的 AI Engine，含 gateway 命令（V10/V36）
- **Codex++**：给 Codex 做请求协议转换，让免 API 模型能在 Codex 做 Vibe Coding（V16/V17）
- **Flex 网关**：客户端与模型间的中间层，稳定无限调工具 + 支持多人并发（V30/V36）
- **OpenCLI**：把网页变命令行，纯代码方式零 Token 采集数据（V29）
- **提示词裁剪工具**：解决网页模型上下文超限（V11）
- **Skill.md**：通用技能文件，让模型按标准 XML 调本地工具 / 生图生视频（V18/V24）

---

## 四、对 WorkBuddy 的映射（统一说明）

- WorkBuddy 的「自定义 API / 自定义提供商」入口 = Hermes 的「自定义介入 API 方式」，**字段同构**（Base URL / Key / 模型名 / 上游协议 Chat Completions）
- 免费模型（GLM 5.2 / Kimi / DeepSeek）经转 API 后，作为**零成本主力或兜底**挂进 WorkBuddy
- 工具调用：优先 XML 格式 + 提示词注入（V22/V24）
- 多 agent 并发：可加 Flex 网关（V30/V36）
- **不依赖本地模型 / Ollama**（BOSS 明确：只接 WorkBuddy + 免费网页端模型）

---

## 五、对 OPC 一人公司 · 跨境选品（重点，融合 V19/V20/V29/V26）

- **选品调研**：用零 Token 选品软件（V19/V20）或 OpenCLI 纯代码采集（V29），对 Ozon / 美客多 / 亚马逊做竞品数据采集 + AI 分析，全程零成本
- **Agent 蜂群架构**：Hermes 的「主 / 子 Agent 上下文隔离」范式（V26）可直接复用到你的蜂群——不同子 Agent 分管不同平台，互不干扰
- **自动化推送**：Hermes Gateway 接飞书 + 定时任务（V25）说明「客户端 + 飞书网关 + 定时」是成熟形态，你已连飞书，可照此做选品报告定时推送

---

## 六、高频坑 / 注意事项

- **代理没开 → HTTP 500 网关无响应**：接网关后报错先查代理是否开启（V30）
- **WSL2 里 `127.0.0.1` 不通**：跨虚拟化边界要用 Windows 主机真实 IP 替换（V31）
- **YOLO 类免确认命令危险**：生产环境保留人工确认，尤其文件删除 / 对外发送（V25）
- **多轮上下文要开**：否则长任务断层（V21）
- **纯代码采集守平台规则**：避免封号（V29）

---

## 七、分篇索引

| 编号 | 主题 | 价值 |
|---|---|---|
| V8 | Cherry Studio 自定义 API 接 Kimi | 范式雏形 |
| V9 | Cherry Studio 接 Kimi（与 V8 重合） | 印证 |
| V10 | OpenClaw 网页模型转 API 实操 | ★核心工具 |
| V11 | 提示词裁剪解决上下文超限 | 配套工具 |
| V12 | 协议转换免 Token 用 GLM（Windows） | 路线 B |
| V13/V14 | 免 API 用 GLM 5.2 接 Hermes 多步无报错 | ★稳定性验证 |
| V15 | GLM 5.2 vs 5.1 + 最省 Token 转换服务 | 选型 |
| V16/V17 | Codex++ 让 Codex 接免 API 做 Vibe Coding | 编码 Agent |
| V18 | 零 Token 用 Hermes 生图生视频 | 多模态 |
| V19/V20 | 电商选品数据采集软件 + 零 Token 接入 | ★跨境选品 |
| V21 | 网页转 API 通用工具 + 多轮上下文 + 零金额 | ★底座说明 |
| V22/V23/V24 | Hermes 接网页模型 + 工具调用 + Skill | 接入手册 |
| V25/V26 | Hermes 效率技巧 + 百条命令（含飞书网关） | 运维/架构 |
| V27/V28/V32/V34/V35 | 与 V23/V22/V18/V14/V13 重复 | 已标重复 |
| V29 | OpenCLI 纯代码零 Token 采集 | ★选品采集 |
| V30 | Flex 中间层无限调工具 | 进阶稳定 |
| V31 | WSL2 网络排错 | 排错 |
| V33 | 作者零 Token 社群推广（非技术） | 情报源 |
| V36 | 零 Token 两路线总览对比 | ★先看这篇 |
