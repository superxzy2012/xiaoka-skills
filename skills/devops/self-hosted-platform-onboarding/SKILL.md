---
name: self-hosted-platform-onboarding
description: Use when 新装平台要摸清能力并判断在蜂群怎么用。
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [platform-audit, onboarding, swarm, comparison, reporting]
    related_skills: [nas-docker-deploy, nanomuse-ops, multi-agent-collaboration, agent-governance]
---

# 自托管平台：摸排 → 落位判断 → 表格化交付

## When to Use

- BOSS 装完一个新平台后说「我进去了，我不会用」「这到底是干嘛的」「在我们的蜂群系统能做什么」
- 要判断一个新平台值不值得接进蜂群、以什么角色接
- 要给已装平台补一份「能力档案」

不适用：部署、排障、改配置 → `nas-docker-deploy`。

## 一、四层取证，别只看 README

按 1→4 顺序，每层都留证据。**只看 README 会漏掉「实际启用了什么」**，只看页面会漏掉「它其实做不到什么」。

| 层 | 拿什么 | 命令 |
|---|---|---|
| ① 运行实例 API | 已启用的专家/模型/设置（最权威） | `GET /api/experts`、`/api/providers/active-model`、`/api/settings/*`、`/api/health` |
| ② 容器内源码路由 | 真实能力边界、未在 UI 暴露的接口 | `ls /app/src/*/api/routers/`、`grep -rn "APIRouter(prefix" /app/src/*/api/routers/` |
| ③ 静态资源 | 连接器/渠道/专家库的全量清单 | `catalog.json`、`i18n/zh.json`、`README.md` |
| ④ 实测驱动一次 | 证明「能被外部调用」，不是设想 | 登录拿 token → WebSocket/REST 真发一句，收到正文 |

要点：

- **清单类信息从 API 拿，别从目录名或 yaml 猜。** 专家库目录里是 yaml manifest，逐个解析又碎又易错；运行实例的 `GET /api/experts` 直接给 `id + name + description{zh,en}`。
- **`i18n/zh.json` 是能力边界的金矿。** 错误码会暴露 UI 上没写的功能：`CHANNEL_KIND_UNSUPPORTED`→有多渠道、`BACKUP_DRIVER_MISMATCH`→有备份恢复、`LDAP_UNAVAILABLE`→支持目录服务、`SETUP_PASSWORD_WRONG`→有向导口令。
- **没有 OpenAPI 不代表接口坏了。** 自托管产品常不暴露 `/openapi.json`、`/docs`，全 404 是常态，直接读源码路由。
- 源码/API 都拿不到时，才退回 README；README 与实跑不一致时**以实跑为准**。

## 二、判断口径：只找「真缺口」，不做功能罗列

每识别一个模块，必须和蜂群现有能力**逐项对照**，标四档：

| 标记 | 含义 | 处理 |
|---|---|---|
| 🟢 真缺口 | 现有系统完全没有（OAuth 连接器生态、向量检索、GUI 操作、多渠道） | 值得接，优先 |
| 🟡 互补 | 有重叠但粒度/形态不同（多专家独立 workspace vs 共享技能的分身） | 看具体场景，标注风险 |
| 🔴 重复 | 现有更好或已跑通（模型网关、cron、飞书入口、深度运维技能） | 明说别用 |

两条硬规则：

1. **新平台几乎从不该「替代」现有系统。** 结论一律落在「当外挂/补充」，落在「替代」上的方案要能解释为什么现有方案失效。
2. **区分「实测通过」和「设想可行」。** 接法表里每行标状态（✅已实测 / 🟡未做但路径清楚 / ⚠️风险高），别把没跑过的写成能力。

## 三、交付格式（BOSS 要求：表格化、好理解）

固定六段，缺一段算没交付：

1. **一句话定位** —— 用「A 是 X，它是 Y」的对照句，抓本质差别（例：蜂群是「一个大脑+很多分身」，它是「很多专家+一个控制台」）
2. **模块表** —— 列：模块 / 干什么 / 你现在的对应物 / 判断（🟢🟡🔴）。**「你现在的对应物」这一列是核心**，没有它表格就退化成产品说明书
3. **对你有用的子集** —— 全量清单里只挑 5–8 个，每个给「落到你的业务上」一句
4. **接法表** —— 列：模式 / 具体怎么接 / 状态 / 收益
5. **不建议做什么** —— 列：别干 / 原因。这段最能建立信任，不能省
6. **上手三步 + 结论** —— 三步要是可点的具体动作；结论一句话给出「当外挂，别替代」这类明确判断

风格：结论先行、emoji 标记、每个判断有依据。**不要复述产品 README 的卖点清单**。

## 四、踩坑

1. **`sed -n "/## .*Features/,/## .*Roadmap/p"` 抓 README 段落经常空** —— 标题词对不上就整段丢掉，且退出码可能非 0 让人误判成命令坏了。直接 `head -70` 或按行号 `sed -n '1,120p'`。
2. **别用 `docker exec` 里的 shell 循环解析 yaml manifest** —— 引号层级一错就静默空输出。优先走 API。
3. **外部桥接看有没有长期 token。** 很多自托管产品只有 JWT（如 24h 有效期、无 PAT/API key），桥接脚本必须每次 `login` 换 token，不能存一次用到底。
4. **「页面能打开」不是「会用」。** 交付前必须真发一轮对话或真跑一次任务，把回复原文贴进报告。
5. **只读摸排不要改状态。** 探能力面时只调 GET；要写配置就说明白并另起一步。

## 五、已建档案

- `references/octop.md` —— Octop（腾讯云开源，MIT）能力面、专家库、与蜂群落位判断、外部调用契约。
