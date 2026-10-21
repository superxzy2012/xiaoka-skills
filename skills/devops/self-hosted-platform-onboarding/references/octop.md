# Octop 能力档案（摸排实测）

腾讯云开源 `TencentCloud/Octop`，MIT，FastAPI + React，自托管多用户 AI 工作台。
部署与初始化配方见 `nas-docker-deploy` §5 / §5.1.1（含 setup 向导 API 顺序、closed-database 坑、WS 验收）。

## 本质定位

「很多专家 + 一个控制台」。每个专家有**独立的 workspace / 技能 / 记忆 / 渠道 / cron**；
蜂群是同一套能力的分身，共享技能库与记忆。差别在隔离粒度，不在模型能力。

## 能力面（实测）

| 模块 | 事实 |
|---|---|
| 专家 Experts | `GET /api/experts` 返回 17 个内置专家，每个带 `description{zh,en}`；可自建，每个独立人格/技能/记忆/渠道 |
| 连接器 Connectors | `catalog.json` 枚举 OAuth/MCP 集成（企查查、腾讯文档、滴滴、飞猪、Notion、Obsidian、Dify、飞书 CLI、企业微信 CLI、Agent Mail 等）；**数量以 catalog.json 实测为准，别背数字** |
| 渠道 Channels | 飞书 / 钉钉 / QQ / 微信 / 企业微信 / Telegram / Discord（i18n 有 `CHANNEL_KIND_UNSUPPORTED`） |
| 知识库 | `APIRouter(prefix="/knowledge-bases")`，文档切块 + 检索，可部署内共享 |
| AgentTeams | 协调者 + 成员的多步协作，**Beta** |
| ACP | 双向：能被 IDE 当 agent 调；也能调 Claude Code / Codex / OpenCode |
| 远程桌面 | 浏览器内控宿主机桌面，可点任意 GUI（风险高） |
| 浏览器 / 终端 AI+ | 内置无头 Chromium、网页终端 |
| 多用户 | JWT 隔离，管理员 + 成员 |
| cron | 自带定时，`GET /api/settings/timezone` 独立配置（默认 Asia/Shanghai，与容器 TZ 无关） |

## 内置专家里对 BOSS 有用的（17 个中挑 6）

| 专家 | 用途 |
|---|---|
| `wechat-ops` 一文多发 | Markdown 一键发布到公众号等平台，微信端走 wenyan-cli 排版 |
| `stock-assistant` 老钱 | A 股行情/基本面/技术面/热点 |
| `office-automation` 小办 | Word/Excel/PPT/PDF，表格清洗与分析 |
| `news-trend` | 70+ 平台热点筛选 + 个性化分析 |
| `ops-engineer` | Linux/K8s/Docker/网络诊断 Shell 专家 |
| `ai-safety-guardian` | PIPL / 等保 2.0 / 数据出境 / 生成式 AI 标识合规 |

其余（腾讯云 CVM 医生、临床学习、育儿、美团、Karpathy 知识库、superpowers 方法论等）与本业务无关。

## 外部调用契约（蜂群 → Octop）

```
POST /api/auth/login  {username,password}     → access_token（JWT，无 PAT/长期 key）
WS   /api/agents/<agent_id>/chat/ws?token=<JWT>
     → {"type":"user_turn","text":"…"}       # 服务端流式回多帧，按 type 归类收集
```

- 无长期 token：桥接脚本每次先 login。
- 默认 agent id = `main`；其余专家 id 从 `GET /api/experts` 取。
- 同一飞书应用只能一个长连接 → 要给它配飞书渠道必须另建独立 app_id/secret，不能抢现有 bot 的。

## 落位判断（结论）

当蜂群外挂，不替代：

1. 🟢 **专家外包** —— 小卡把重活（长文排版、A 股复盘、Excel/PPT 加工）派给对应专家，不占自己上下文（已实测可驱动）
2. 🟢 **连接器补缺** —— 企查查查供应商工商底细、腾讯文档协作，蜂群完全没有 OAuth 生态
3. 🟢 **RAG 知识库** —— Obsidian vault 灌进去做语义检索（现在只有 grep 关键词）
4. 🟡 **GUI 手** —— 远程桌面能点任意软件，但等于把机器交出去

别用它做：替代 13 bot 蜂群（它没有 A2A 总线概念）、替代小卡的深度技能（抖音入库/字幕/NAS 运维/Ozon 上架）、
当模型网关（OmniRoute 更强）、暴露公网（无 TLS + 单机 JWT + 远程桌面）。
