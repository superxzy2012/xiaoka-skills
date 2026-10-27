---
name: octop-ops
description: Use when 操作或排障 NAS 上的 Octop 专家平台。
---

# Octop 运维（NAS 8088）

Octop = 「很多专家 + 一个控制台」的 agent 平台。在蜂群里当**第四外挂**：专家外包、RAG 检索、外网抓数、MCP 连接。**不替代**蜂群 A2A 总线。

## 0. 坐标

| 项 | 值 |
|---|---|
| 地址 | `http://192.168.199.2:8088` |
| 容器 | `octop`（`sudo -n docker` 走 SSH `DY@192.168.199.2`） |
| 数据 | 容器内 `/data/.octop`；DB `/volume2/2-AI/octop/octop.db`（SQLite） |
| 凭据 | `/opt/data/secrets/octop_admin.txt`（600，`admin` / 邮箱 / 密码） |
| 公共库 | `/opt/data/lib/oct_lib.py`（login / call / ws_chat）。🔴 **绝不能放 `/opt/data/cache/scratch/`**——该目录 24h 自动清理，库被删后 cron 连挂数百次（2026-10-25 实测 474 连错 ModuleNotFoundError）。worker 与 CLI 的 `sys.path.insert` 都指向 `/opt/data/lib`。WS 正文只取 `type==token` 的 content 增量、跳过 reasoning/控制帧，结束帧 `type==done`。 |
| CLI | `/opt/data/bin/octop`（ls / health / kb / ask / team） |

## 1. 一条命令派活

```bash
/opt/data/bin/octop health
/opt/data/bin/octop ls
/opt/data/bin/octop ask 老钱 "查上证指数和成交额"
/opt/data/bin/octop ask 小安 "便携榨汁杯进俄罗斯要哪些认证"
/opt/data/bin/octop team XJWVMB "评估便携榨汁杯能不能在 Ozon 卖"
/opt/data/bin/octop kb
```

别名表在 `/opt/data/memories/octop_agents.json` + CLI 内 `ALIAS`。

**提问必须带「输出格式后缀」**，否则 WS 回包会混进英文思维链和搜索步骤（`Let me search…` / `Search knowledge base for…`），没法直接给人看。固定后缀：

```
直接给最终答案，不要输出思考过程、不要列搜索步骤；60 字内，末尾注明依据文件名。
```

这句同时兼做 RAG 的证据要求：让 agent 报文件名，才能回 vault 原文核对它有没有编。

⚠️ `/opt/data/bin/octop ask` **不会自动加这句**——要干净结果就自己把后缀拼进问题，或直接调 `oct_lib.ws_chat()`。

⚠️ **后缀只是缓解，根因在 `ws_chat` 的帧过滤**：WS 事件流里有独立的 `reasoning` 帧，`ws_chat` 把所有 `text`/`delta`/`content` 字段无条件拼接，于是思考过程被当成正文返回（`kinds` 里 `reasoning` 帧数可达 251）。要彻底干净，在 `ws_chat` 循环里跳过 `t == "reasoning"` 的帧再拼正文；只加提示词时，模型仍可能先吐一段英文思考再给答案。

## 2. API 速查（都带 JWT，`oct_lib.call()`）

全量能力面（270 条路由 / 272 个子代理 / 27 个连接器 / 27 个插件 + 复现摸排命令）见 `references/capability-surface.md`。

| 目的 | 调用 |
|---|---|
| 登录 | `POST /api/auth/login {username,password}` → token |
| agent 列表 | `GET /api/agents` |
| 从专家建 agent | `POST /api/agents/from-expert/{expert_id}` body `{name,description,default_model,knowledge_base_ids,mcp_servers}` |
| 建团队 | `POST /api/teams {name,member_ids,default_model,welcome_message}` → `team_id` |
| 对话 | `ws://…/api/agents/{agent_id}/chat/ws?token=` → `{"type":"user_turn","text":"…"}` |
| 建知识库 | `POST /api/knowledge-bases {name,description,shared}` |
| 灌文档 | `POST /api/knowledge-bases/{kb}/documents/text {name,format:"md",content}` |
| 文档列表 | `GET /api/knowledge-bases/{kb}/documents`（有 `path`/`status`/`chunk_count`） |
| 开 RAG | `PUT /api/knowledge-bases/feature {enabled,model,backend:"onnx"}` + `POST /onnx-download` |
| 挂 MCP | `PUT /api/connectors/custom-mcp {servers:{名:{transport:"streamable_http",url}}}` |
| 装技能 | `POST /api/agents/{agent_id}/skills/hub/install {skill_name:<registry slug>,enable:true}` |
| 装插件 | `POST /api/plugins/market/{plugin_id}/install` |
| 记忆统计 | `GET /api/agents/{agent_id}/memory/stats/counts` |
| 记忆配置 | `PUT /api/agents/{agent_id}/memory/extract-config {memory_enabled,extract_trigger_mode:"idle",extract_idle_seconds,aux_model:"OmniRoute/a2a/deepseek-v4.1-flash"}` |
| 记忆原子/候选 | `POST /api/agents/{agent_id}/memory/atoms/list`、`.../candidates/list` |
| 子代理目录 | `GET /api/subagent-catalog`、`/api/subagent-catalog/divisions`（272 个，按 division 分组） |
| 装子代理 | `POST /api/agents/{agent_id}/subagents/install {slug, locale:"zh"}` |
| 技能中心 | `GET /api/skills/hub/search?q=&limit=`、`/api/skills/hub/rankings` |
| 插件市场 | `GET /api/plugins/market`（已装的标 `INSTALLED`） |
| 连接器目录 | `GET /api/connectors/catalog`（`auth_kind`/`oauth_ready`/`credential_fields`/`auth_hint`） |
| 决策模型 | `PUT /api/settings/decision`（JEV 只当分类层） |
| 浏览器 | `POST /api/browser/install` → 复核 `GET /api/browser/env-status` |
| 用量 | `GET /api/usage/summary` |
| ACP 状态 | `GET /api/acp`（7 个 runner） |

⚠️ **路径里的 `{agent_id}` 是字符串短码（`main`/`CMW4WR`），不是 `GET /api/agents` 返回的 `id` 字段。**
`GET /api/agents` 每项同时有 `id`（数字 1…N）和 `agent_id`（短码）——用 `x['id']` 拼 `/api/agents/{…}/…` 会**全部 404**，而且循环里每个 agent 都 404，看起来像端点坏了。取 `x['agent_id']`。

## 2b. 打开 ACP runner（Claude Code / Codex）

出厂 7 个 ACP runner 全 `enabled=false`，根因是容器没有 node/npx——不是功能不存在，补上就能开：

```bash
# 1) Node 装到持久化目录（/data/.octop 是 bind mount，重建容器不丢）
#    nodejs.org 走 7891 代理会 SSL 失败（curl exit 35）→ 换 npmmirror 且 --noproxy "*"
ssh DY@192.168.199.2 "sudo -n docker exec octop sh -c 'mkdir -p /data/.octop/runtime && cd /data/.octop/runtime && curl -sL --noproxy \"*\" -o node.tar.xz https://cdn.npmmirror.com/binaries/node/v22.14.0/node-v22.14.0-linux-x64.tar.xz && tar -xf node.tar.xz && mv node-v22.14.0-linux-x64 node && rm -f node.tar.xz && /data/.octop/runtime/node/bin/node -v'"
# 2) 软链 + registry（缺软链时 npm 报 env: 'node': No such file or directory——npm 的 shebang 找不到 node）
ssh DY@192.168.199.2 "sudo -n docker exec octop sh -c 'for b in node npm npx; do ln -sf /data/.octop/runtime/node/bin/\$b /usr/local/bin/\$b; done && npm config set registry https://registry.npmmirror.com'"
```

**验活必须打握手，不能只看 `--help`**（`--help` 可能 exit 0 且零输出，证明不了任何事）：

```bash
printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":1,"clientCapabilities":{}}}' \
 | timeout 90 npx -y @zed-industries/claude-agent-acp
```

真跑起来会回 `protocolVersion` + `agentInfo`（带版本）+ `agentCapabilities`（image / embeddedContext / mcp http+sse / fork / resume）。`authMethods: []` 说明认证不预置，靠环境变量注入。

⚠️ **握手通过 ≠ 已可用**：没给凭据前 runner 起得来，一调模型就 401。交付时说「链路已通、只差凭据」，别说「Claude 已接好」。

### 零成本路线：OmniRoute 免费模型跑 Claude Code（已端到端跑通）

OmniRoute（`20128`）**暴露 Anthropic 原生 `/v1/messages`**。探活发空 body 的 POST —— 回 `401` = 端点存在只是缺 key，回 `404` = 根本没这条路由（这个 401/404 判别法适用于任何网关的协议兼容性排查）。

接线四步，缺一步都跑不通：

1. **全局 runner**：`GET /api/acp` 拿全量 → 改 `runners.claude_code` → `PUT /api/acp`。设 `enabled=true`、`trusted=true`、`command:"npx"`、`args:["-y","@zed-industries/claude-agent-acp"]`，`env` 里放 `ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`（OmniRoute key 在 Octop DB `providers` 表 id=3 的 `api_key`）+ `HOME=/data` + 完整 `PATH`。
2. **每个 agent 单独开**：`GET`/`PUT /api/agents/{aid}/acp`，设 `tool_enabled=true` 并在该 agent 的 `runners.claude_code` 里重复同一份 env。**全局开了不等于 agent 能用**——agent 级配置独立。
3. **模型写 settings.json**：`/data/.claude/settings.json` = `{"model":"openrouter/minimax/minimax-m3.1-flash:free"}`。
4. **验活要真产出文件**：让它写一个文件，再进容器把文件内容读回来核对，别信 agent 自报「已完成」。

**三个必踩的坑**：

- **`No active credentials for provider: antigravity`（401）**：Claude Code 默认发 `claude-opus-4-6`，OmniRoute 把未知模型名路由到没配凭据的 antigravity provider。**只有 settings.json 的 `model` 字段能改**。
- **`ANTHROPIC_MODEL` 无效**：`claude-agent-acp` 只读 `ANTHROPIC_AUTH_TOKEN`/`ANTHROPIC_BASE_URL`/`ANTHROPIC_CUSTOM_HEADERS`，不认 `ANTHROPIC_API_KEY`，也不认 `ANTHROPIC_MODEL`。
- **卡死到超时**：工具调用后 ACP 发 `session/request_permission` 等客户端批准，没人回就挂住（实测挂满 300s）。自建客户端必须收到就回 allow；Octop 侧靠 `trusted:true`。

**先别急着上 ACP**：Octop agent 自带 `execute` 工具，写脚本/建文件一分钟内就能干完，不需要 ACP。ACP 的价值是**完整编程 agent**（读整个项目、多轮改代码、跑测试）——小任务用 execute，重构才开 ACP。对外报价也要讲明：跑的不是 Claude 本体，prompt 适配有折扣。

配置 JSON、stdio 最小客户端流程、免费模型候选表、ACP 是否真被调用的判别法 → `references/acp-claude-code.md`。

## 2c. 接飞书：扫码创建机器人

见 §6.7（唯一权威版本，含完整流程与坑）。

## 2d. 用固定短码注册自定义专家（Agency 八专家实战）

HTTP `POST /api/agents` **不接受自定义 agent_id**（自动生成 6 位随机码）。要固定短码（如 `PRICE`）必须走容器内 embedded runtime 直接 `AgentCreateSpec(agent_id=...)`：

```python
from octop.cli.repl.embedded_session import embedded_runtime
from octop.infra.agents.manager import AgentCreateSpec
async with embedded_runtime() as server:
    await server.app_runtime.agent_registry.create(AgentCreateSpec(
        name="定价分析师 · 单位经济", agent_id="PRICE", user_id=1,
        default_model="a2a/deepseek-v4.1-flash", template_name="general-assistant"))
```

### 🔴 铁律：「写入成功」≠「已生效」

任何绕过 HTTP API 的写入（embedded runtime 建 agent、直接改 DB、改容器内文件、改 compose）**写完之后必须 reload / 重启 + 回读**。写入返回成功只证明落盘，运行中的进程可能完全不知道有这回事——表现是「接口 200、日志无错、调用永远不回」。

### 三个必踩坑（按出现顺序）

1. **embedded create 只写 DB，运行中的 server 不认识新 agent** → WS `[accepted]` 但**永不回话**，PING 挂到超时（表现为 rc=124 / 空输出），日志里只有 accepted 没有报错。
   **必须补一步**：`POST /api/agents/{id}/reload`（204）。之后 PING 才通。
2. **`template_name` 必须是 22 个内置专家 id 之一**（`general-assistant` / `stock-assistant` / `office-automation` / `news-trend` / `ops-engineer` / `ai-safety-guardian` / `multi-agent-orchestrator` / `wechat-ops` …）。传不存在的名字（如 Agency 的 `pricing-analyst`）**不报错，只 logger.warning 后 skip** → 不生成 `.octop/manifest.json` → bootstrap 卡死。查全量：`GET /api/experts`。
3. **`agent_id` 是 workspace 目录名，正则 `^[a-zA-Z0-9][a-zA-Z0-9_-]{1,62}[a-zA-Z0-9]$`（3-64 字符）**。`QA` 只有 2 字符 → `AGENT_ID_INVALID`。绕法：注册成 `QA1`，CLI/worker ALIAS 里把 `QA`/`质检`/`小质` 都映射到 `QA1`，对外仍叫 QA。

### 正确顺序（已验证）
```
① 备份 DB + agents/ 目录 + CLI/worker
② embedded create（agent_id=CODE, template_name=<内置id>）
③ 覆盖 workspace 的 SOUL.md / IDENTITY.md 为自定义 persona
④ 改 .octop/manifest.json 的 label.zh / description.zh（否则界面显示基底模板名）
⑤ POST /api/agents/{id}/reload   ← 缺这步必挂
⑥ 逐个 WS PING（首次含 bootstrap，慢 40-125s；之后快）
```
⚠️ `reg.delete()` 是 **async**，不 `await` 会静默不删，接着 create 就报 `agent name ... already in use`。
⚠️ 重建前先 `shutil.rmtree` 旧 workspace，否则残留文件干扰 seed。
⚠️ 别用 `docker cp /dev/stdin` 传脚本进容器（会建成指向 `/proc/self/fd/0` 的坏软链）——用 `echo <base64> | base64 -d > /tmp/x.py`。

## 3. 坑（全部实测踩过）

1. **容器默认无外网**：HF/模型下载、专家抓行情全失败。compose 里加 `HTTP_PROXY`/`HTTPS_PROXY=http://192.168.199.2:7891` + `NO_PROXY` 白名单后 `docker compose up -d --force-recreate`。
2. **文档名只留文件名**：`name` 传 `11-提炼沉淀/x.md`，落库后 `path` 变成 `x.md`，目录被剥掉。同名文件（跨目录）→ `409 KNOWLEDGE_NAME_TAKEN`（报错文案写「同名知识库」，实际是文档重名）。要保留区分就自己把目录拼进文件名：`11-提炼沉淀__x.md`。
3. **vault 里部分笔记是 600 且非本用户所有**：直接 `read_text` → `Permission denied`。绕法：`docker run --rm -v /volume2/2-AI:/ai alpine` 以 root 拷到 `a+r` 的临时目录再上传（`sudo -n docker` 可用，`sudo -n cat/cp` 不可用）。
4. **灌库上传快、嵌入慢（关键调优）**：POST 0.3 s/篇，但 1.0.2 版 `/app/src/octop/infra/knowledge/jobs.py` 里 `INDEX_CONCURRENCY = 1`，实测只有 ~2.3 篇/min，700 篇要 5 小时。改成 6 后 ~11.6 篇/min（NAS 4 核能吃住）。改法（持久化，不怕 recreate）：
   ```bash
   # 1) 容器内 sed 改 → 2) 拷到宿主机 → 3) compose 加只读 bind mount → 4) up -d
   sudo -n docker exec octop sed -i 's/^INDEX_CONCURRENCY = 1$/INDEX_CONCURRENCY = 6/' /app/src/octop/infra/knowledge/jobs.py
   sudo -n docker cp octop:/app/src/octop/infra/knowledge/jobs.py /tmp/jobs_patched.py
   sudo -n docker run --rm -v /volume2/2-AI/octop:/w -v /tmp/jobs_patched.py:/src.py alpine sh -c 'mkdir -p /w/patch && cp /src.py /w/patch/jobs.py'
   # compose volumes 里加：- /volume2/2-AI/octop/patch/jobs.py:/app/src/octop/infra/knowledge/jobs.py:ro
   cd /volume2/2-AI/octop && sudo -n docker compose up -d
   ```
   ⚠️ 升级镜像前必须删掉这条 mount，否则新版 `jobs.py` 被旧文件盖住。
   ⚠️ 队列存 DB，重启/recreate 不丢（实测两次），可以放心重启；但**重启会断掉正在跑的 WS 问答**，测问答时别同时重启。
5. **知识库 `max_documents` 默认 100**：`PUT /api/knowledge-bases/{kb} {max_documents:5000}` 先放开，否则第 101 篇起被拒。
6. **技能安装要 registry slug**，不是显示名；传中文名 → 404 `not found in SkillHub`。先 `GET /api/skills/hub/search?q=` 拿 slug。**body 的键必须是 `skill_name`**（`{skill_name:<slug>, enable:true}`）；写成 `{"slug":…}` → 422 `skill_name Field required`——报错只说字段缺失，不提示正确键名。
7. **插件安装走 `market/{plugin_id}`**，不要往 `/api/plugins` POST（要 `url` 字段，传 id 一律 422）。
8. **ACP 7 个 runner 默认全 `enabled=false`**，根因是容器出厂没有 node/npx——**不是功能缺失**，装上就能开（见 §2b）。别把配置默认值当能力结论写进交付文档：曾据此写过「别指望」，后来 Node 一装 `claude-agent-acp` 握手直接通过。
9. **同一 agent 的 WS 会话会去重**：`ws_chat` 只接 `?token=`，没有 session 参数，复用 agent 默认对话。同一句话问第二次，模型会看到 dedup 标记并回「重复问题/无待办」，答案串题。**测 RAG 时每轮换一个 agent**（如第一轮 CMW4WR、第二轮 Q8NY3B），或建一个一次性 agent。
10. **RAG 会把相邻数字串错**：实测「上传历史保留 14 天」被答成 15 天（串了同文件里「导出历史 15 天」）。答案带文件名 ≠ 答案对，**引用前必须 grep 原文对一眼**（ground-truth-discipline）。
11. **`PATCH /api/teams/{id}` 返回 200 但 `knowledge_base_ids`/`mcp_servers` 不落库**（回读是 `None`）。团队不携带 KB/MCP，知识库要挂在**每个成员 agent** 上（`PATCH /api/agents/{aid}` 或建 agent 时传）。团队只负责拆活派活。
12. **没有版本查询端点**：`/api/update/check`、`/api/status`、`/api/version`、`/api/settings/version` 全 404。确认版本只认 `docker inspect octop --format '{{.Config.Image}}'`。
13. **RAG 命中率别在索引没跑完时下结论**：`ready < total` 时同一批题会明显偏低（实测同一题在索引半成时答「未收录」，全成后能答对）。验收前先 `GET /documents` 看 `ready == len(docs)`。题库见 `references/rag-acceptance.md`。
14. **记忆提炼被 `extract_interval_seconds` 卡住**：默认 `21600`（6 小时），即使 idle 触发配好了，6 小时内也只提炼一次，看上去像「只记不炼」。要「说完就炼」压到 `600`。判据全在 `GET .../memory/stats/counts` 的 `last_extract_run`：`llm_calls>0 && events_extracted>0` = 提炼真在跑；此时 `candidates=0` 才是模型判定「不算长期事实」，不是链路坏。
15. **测试痕迹要真删干净**：`DELETE /api/teams/{id}` 与 `DELETE /api/knowledge-bases/{id}` 都返回 204，删完回读列表确认。摸排用的测试团队/测试库别留给 BOSS「开箱即用」。
16. **子代理安装端点是 `/subagents/install`，body 键是 `slug`**：`POST /api/agents/{aid}/subagents/install {slug:<catalog slug>, locale:"zh"}`。往 `/api/agents/{aid}/subagents` POST 不管 body 怎么变都失败——**猜端点前先 `grep -rn "subagents" /app/src/octop/api` 再 `sed -n '<行>,<行>p'` 读路由签名**，比试三四种 body 快得多。
17. **`POST /api/browser/install` 客户端超时 ≠ 失败**：返回 `-1 TimeoutError` 后查 `GET /api/browser/env-status` 常常是 `browsers_ok: true`（Chromium 落 `/root/.cache/ms-playwright/chromium-*`）。装完只认 env-status，别因超时重装。
18. **决策模型是 `PUT /api/settings/decision`**：`{enabled,provider:"jev",endpoint:"http://192.168.199.2:8082",model:"jev-latest",threshold:0.6,tool_min_count:8}`，PUT 完 GET 复核。JEV 只做「这一轮要不要调工具」的分类层，不接管主模型。
19. **`PATCH /api/agents/{aid}` 回 200 ≠ persona 生效**：8 个 Agency agent 建好后 `system_prompt` 全是 **null**，SOUL.md/IDENTITY.md 只在 workspace 文件里、**不进模型上下文**，于是模型拿基底模板名自报（「助理」「测试工程师」）。修法：`PATCH {"system_prompt": "# 你是<岗位>（code <CODE>）\n<职责>\n\n输出纪律：…"}` + `POST /api/agents/{aid}/reload`，然后**问一句「你是哪个岗位」验回显**——只看 200 和字段长度不够。
20. **别用「轻量」形容 Octop 的成本**：`GET /api/usage/summary` 实测近 30 天 **62,399 tokens/轮**（缓存命中 77%，真新增约 7k/轮）。对外讲成本一律引这个数——凭感觉说「几百到几千」会被自己的实测打脸。

## 3b. 升级镜像

compose 文件在宿主机 `/volume2/2-AI/octop/docker-compose.yml`（= 容器内 `/data/.octop/docker-compose.yml`，同一文件）。Hermes 用户改不了 NAS 上的文件，用 alpine 容器代改：

```bash
ssh DY@192.168.199.2 'sudo -n docker run --rm -v /volume2/2-AI/octop:/w alpine sh -c "cp /w/docker-compose.yml /w/docker-compose.yml.bak && sed -i \"s|octop:1.0.2b7|octop:1.0.2|\" /w/docker-compose.yml"'
ssh DY@192.168.199.2 'cd /volume2/2-AI/octop && sudo -n docker compose pull && sudo -n docker compose up -d'
```

升级前：① 备份 DB `cp /data/.octop/octop.db /data/.octop/backups/octop-<旧版本>-$(date +%Y%m%d-%H%M).db`；② **删掉 §3.4 的 `jobs.py` bind mount**，否则新版代码被旧补丁盖住。升级后复查：health 200、agent 全 running、`INDEX_CONCURRENCY` 回到 1（需要就重新打补丁）、KB `doc_count` 不变。

## 4. 记忆「只记不炼」是误判

`extract-config` 默认 `aux_model=null` → 抽取不调模型。配上 `OmniRoute/a2a/deepseek-v4.1-flash` + `extract_trigger_mode=idle` + `extract_idle_seconds=120` + `extract_interval_seconds=600` 后，`last_extract_run` 会出现 `llm_calls>0`、`events_extracted>0`。但**只有含长期事实的对话才产出 candidates**——问「25 对不对」这种不会有原子。候选需 `:promote` 才进 atoms。

配置要写给**每个 agent**（`GET /api/agents` 遍历取 `agent_id`），团队对象本身不持有记忆配置。

⚠️ **两个 id 别搞错**：`GET /api/agents` 返回的 `id` 是数字 1..N，`agent_id` 才是 `main`/`4GK9GF` 这种短码。用数字 `id` 调 `memory/extract-config` 全 404（踩过，白跑一轮 10 个）。

**实测证据（2026-10-21）**：对小调 `4GK9GF` 说 4 条长期偏好，2 分钟后 `atoms=4`，每条带 `assertion` + `verbatim_quote` + `search_terms`、`confidence=high`——**真提炼，不是摆设**。

- 读：`POST /api/agents/{aid}/memory/atoms/list`，正文字段是 **`assertion`**（不是 content/text）
- 作废：`POST /api/agents/{aid}/memory/atoms/{atom_id}:deprecate` → 200 `status=deprecated`
- 隐私：记忆是每个 agent 独立的。**别把 BOSS 姓名/城市/身份灌给平台 agent**（违反「个人信息不共享给其他 agent」），只灌业务规则（毛利率红线/中文/执行风格），身份类 atom 用完 `:deprecate` 清掉。

## 5. 团队派活是异步的

`team` 一问只返回协调者的**派活说明**，成员结果要回团队会话里看。别把「已派给 X」当最终答案交付给 BOSS。

没有 `/api/teams/{id}/jobs`、`/api/teams/{id}/sessions`（全 404）——`teams.py` 只有 `GET/POST /teams`、`GET/PATCH/DELETE /teams/{id}`、`GET /teams/template`。要看成员结果只能对团队 agent 再发一轮 WS（`ws_chat(team_id, "汇总一下刚才各成员的结果")`），或直接问被派活的成员。

## 6. 接入蜂群 A2A 总线

Octop 在 A2A 里的标准 id 是 **`octop`**（别名 `章鱼`）。身份卡 `/opt/nas/volume2/2-AI/A2A/agents/octop.md`。

### 6.0 🔴 回执必须真 push，工作副本绝不能放 scratch

**「写到 NAS 本地 A2A/outbox」≠「上了总线」。** 正本是 Gitea `anc/a2a-bus`，本地共享目录 `/opt/nas/volume2/2-AI/A2A` **不是 git 仓**。

- 工作副本固定用 **`/opt/data/a2a-bus`**（`a2a_commit.py` 的 `WORK`）。曾写 `WORK=/opt/data/cache/scratch/a2a-dispatch`，**scratch 24h 自动清理**把仓删了 → commit 从未发生，对端 `cat-file` 永远 404。
- 交付后自检三连（贴原文，不得改写）：
  ```bash
  git -C /opt/data/a2a-bus log --oneline -3
  git -C /opt/data/a2a-bus status --short
  git -C /opt/data/a2a-bus push origin HEAD:main   # 贴 rc + 最后三行
  git cat-file blob <sha>:outbox/receipt_<ref>_<from>_<ts>.json | head
  ```
- **`results/` 在正本有（29+ 文件），公共镜像不带**。回执里 `result_file` 必须写**相对仓根**的路径（`results/result_….md`），否则对端无从核。
- `result_sha256_8` 要与实际文件逐字节对得上：`git cat-file blob <sha>:<path> | sha256sum`。**改了 result 必须告知 sha 已变**，不能默默换值。
- 🔴 **交付物不可变**：已 push 的回执/result 不改历史字段。需修订就写新回执 `…_r2.json`，带 `revision` / `supersedes` / `prev_result_sha256_8` / `result_sha256_8` / `reason`，由旧值指向新值——对端才能同时核到两版。
- **镜像不带 `results/`**（正本递归 1519 文件，含公司线业务内容，有泄露面）。要给外部单份读，复制到 `reports/` 或单独放行，不整目录开。
- 对账口径：`git ls-tree -r <ref> --name-only | grep -c '^results/'`（递归），**不是** `ls results/ | wc -l`（非递归，两回事）。

## 6.1 架构（为什么不用 Octop 自己轮询）

Octop 容器看不到 A2A 共享盘（没挂 `/volume2/2-AI`），所以**由小卡侧代跑 worker**：Hermes 容器读 `inbox/` → 调 Octop WS → 回执写 `outbox/`。

| 件 | 路径 |
|---|---|
| worker | `/opt/data/bin/octop_a2a_worker.py`（单次扫描即退出） |
| 包装 | `/opt/data/bin/octop_a2a_poll.sh`（显式调 venv python + `--quiet`） |
| 常驻守护 | `/opt/data/bin/octop_a2a_daemon.sh`（30s 一轮，flock 单实例，`INTERVAL=${OCTOP_POLL_INTERVAL:-30}`） |
| 健康检查 | `/opt/data/bin/octop_healthcheck.sh`（+ cron `9491e8eba0db` every 5m） |
| 群内直触发 | `/opt/data/bin/octop_grp.py`（见 §6.8） |
| cron 副本 | `/opt/data/scripts/octop_a2a_poll.sh`（**cron 只收相对路径**） |

**30s 周期只能用常驻守护，不能用 cron**：调度器 interval 只到分钟粒度。改用守护后**必须把旧 cron `f96e2da0aa99` 置 paused**，否则两套轮询并发抢同一批任务（靠锁不会双跑，但会互相 SKIP 造成「投了没人处理」的假象）。

守护要点：

- `flock` 锁 `/opt/data/logs/.octop_poll_daemon.lock` 保证单实例；重复启动直接退出，不报错。
- `--quiet` 跑 worker，输出里只 `grep -F '【OCTOP:'` 转管理群，其余进本地日志 `/opt/data/logs/octop_a2a_poll.log`——**别把 IDLE/SKIP 转发出去**，30s 一次会刷屏。
- 用 `terminal(background=true)` 起，别用 `setsid`（`setsid` 经 ssh/包装层常返回 exit -1 但进程其实起了，误判成失败）。
- 判活：`pgrep -fc octop_a2a_daemon.sh`。**pid 变了就是重启过**，别拿旧 pid 当活着的证据。

**healthcheck 判据三合一**（缺一条就漏）：`/api/health` 返回 `ok:true` + `agents_running >= 注册表推导值` + `pgrep -fc octop_a2a_daemon.sh` 非 0。异常时自动拉起守护并往群里发 `⚠️【OCTOP:HEALTH】`。容器重建后 agent 全部消失、守护静默空转——这是最容易被忽略的断点，只有 agents 计数能发现。

四条硬规矩（判据必须能自证，否则没人说得清「这个数字是谁定的」）：

1. **阈值不许手写常量，从真相源推导**：`GET /api/agents` 取 `agent_id` 去重计数（`/opt/data/bin/octop_expect.py`），增删 agent 自动跟随。写死 `17` 或把 `OCTOP_EXPECT_AGENTS` 当默认值，下次扩容就变假告警、缩容就变假绿。
2. **state 里带来源字段**：`expect_agents` / `expect_source`（`registry`｜`override`｜`unreachable`）。🔴 **`state/` 是镜像公共面，不放内部标识明细**（agent code/open_id），ids 明细另落 `reports/octop-expect-latest.json`（正本可读、不进镜像），state 用 `expect_detail` 指针指过去。推导失败判 `expect_unreachable`，**不要**回退到默认数字——那会让「探不到注册表」伪装成健康。
3. 🔴 **测试注入永不写共享审计通道**：验告警态可以用 `OCTOP_EXPECT_AGENTS=99 sh …`，但 override 只写本地 state、**不 commit 不 push**（push 前置 `[ "$EXPECT_SOURCE" != "override" ]`）。曾把测试值推上正本总线，对端看到 `agents_running=17<99` 只能追问「是不是把阈值调低了刷绿」——审计通道被测试污染，真实告警也失去可信度。已入 `PROTOCOL.md` v2「测试态永不推正本」。
4. **变更判据用指纹不用时间戳**：`ts_utc` 每轮都变，整文件比对或无条件 commit 会 5 分钟一条垃圾 commit，把真告警淹没。指纹 = `status|agents|expect|source|daemon|problem|cksum(EXPECT_JSON)`（末项保证数量不变但成员换了也触发），变了才推。

另：判据脚本在 NAS 本地、对端看不到，把快照 + 推导说明提交到总线 `reports/`（`octop_healthcheck.sh` / `octop_expect.py` / `octop_mirror_lag.py` / `octop-health-expect-derivation.md`），改判据才有 `git diff` 可追。协议层规矩（交付物不可变 / 测试态永不推正本 / 公共面脱敏 / 回执 `result_visible_in_mirror` 字段 / 公共面指针须配 `*_in_mirror:false` / 镜像新鲜度只认 GitHub API contents 不认 raw CDN）在总线 `PROTOCOL.md` v2。

**镜像滞后告警归 QUEEN cron `4eb7d1003821`（10m，阈值 lag>45min / state 失配>30min），小卡侧 healthcheck 不重复挂镜像判据**（双套告警互相刷屏）。本地自查用 `reports/octop_mirror_lag.py`（v4）：正本读本地工作副本 `origin/main`，镜像 git-first（只读浅克隆 `/opt/data/a2a-mirror-watch` 读 FETCH_HEAD）+ **api.github.com 降级**（仅 git 失败时才走，先读 `X-RateLimit-Remaining`，为 0 绝不硬闯）；输出 `mirror_src: git|api` 标明来源；3 次重试 + `http.lowSpeedLimit=1000/lowSpeedTime=20`（传输阶段）；取不到回 `verdict=INCONCLUSIVE`（探针存疑，**不告警**，限流 403 也归此——「限流≠停摆」）；`lag_min` 钳到 >=0。

镜像探针五坑（2026-10-27 实测）：①**不用 `api.github.com` 匿名 REST——60 次/小时**，耗尽 403 会被误读成镜像停摆；②不用 `raw.githubusercontent.com` 判新鲜度——CDN 缓存陈旧造成假阴性（QUEEN 撤回的那条），只认 API contents 或 git；③Gitea 匿名 API 404、creds.txt 的 arthur token 对 API 401（git 凭证可用、API token 不可用是两回事）；④`github.com:443` 出网不稳（一次 fetch 卡 133s、下一次 1.6s 成功，抽风型），必须重试 + 硬 timeout；⑤🔴 **`http.connectTimeout` 不是 git 配置键，写了被静默忽略——不报错也不生效，造成虚假安全感**（QUEEN 黑洞 IP 实测：带与不带均 25s 才被外部 timeout 杀）。connect 阶段（一个字节都没传时 lowSpeed 判据不触发）唯一有效兜底是**调用方 subprocess `timeout=`**；`http.lowSpeedLimit/lowSpeedTime` 只管已在传输的阶段。

深度（state 字段表、推导器实现、三个自证实验）：`references/healthcheck-alerting.md`。

### 6.2 子路由（写在信封 `to` 里）

| `to` | 派给 |
|---|---|
| `octop` / `octop:小通` | `main` 通用助手（默认） |
| `octop:小安` / `octop:CMW4WR` | 合规哨兵（Ozon 禁售/认证/EAC） |
| `octop:小热` / `octop:JF6ADQ` | 热点雷达（外网抓数、AI 热点） |
| `octop:小办` / `octop:Q8NY3B` | 办公自动化（表格/文档） |
| `octop:老钱` / `octop:TAQG6V` | 证券观察员（A 股行情） |
| `octop:小维` / `octop:X1N8RQ` | 运维工程师 |
| `octop:阿文` / `octop:9VQHTY` | 一文多发 |
| `octop:小调` / `octop:4GK9GF` | 任务编排 |
| `octop:team:XJWVMB` | 跨境选品小队（多专家协同） |

**Agency 八专家**（固定短码，注册方式见 §2d）：

| `to` | 派给 |
|---|---|
| `octop:小定` / `octop:定价` / `octop:PRICE` | 定价分析师 · 单位经济 |
| `octop:小供` / `octop:供应链` / `octop:SUPPL` | 供应链策略师 · 备货物流 |
| `octop:小增` / `octop:增长` / `octop:GROW` | 增长黑客 · 低成本获客 |
| `octop:小搜` / `octop:SEO` | SEO 策略师 · 搜索关键词 |
| `octop:小号` / `octop:公众号` / `octop:WXGZH` | 公众号运营经理 · 选题涨粉 |
| `octop:小抖` / `octop:抖音` / `octop:DOUY` | 抖音策略师 · 短视频直播 |
| `octop:小质` / `octop:质检` / `octop:QA` / `octop:QA1` | AI 质检专家 · 产出质量门禁 |
| `octop:小本` / `octop:本地化` / `octop:LOC` | 本地化策略师 · 跨境适配 |

🔴 **新增/改名 agent 必须四处同时改，少一处就是静默错路由**：① DB `agents.agent_id` ② workspace 目录 `/data/.octop/agents/<CODE>/` ③ CLI `/opt/data/bin/octop` 的 `ALIAS` ④ worker `octop_a2a_worker.py` 的 `ALIAS`；另加 `octop_agents.json`、`octop_grp.py`。改完各跑一次 `octop:别名` 实测——**别名表里的短码写错不会报错，只会静默路由到不存在的 agent 然后超时**（曾把 `团队` 指到已删的 `WHEB5R`）。

### 6.3 任务信封

```json
{
  "task_ref": "T-20261021-001",
  "from": "xiaoka",
  "to": "octop:小热",
  "ts": "2026-10-21T11:30:00+08:00",
  "type": "task",
  "priority": "P1",
  "instruction": "给 2 条今天值得看的 AI 热点，每条一句话，带来源。",
  "deadline_hours": 2
}
```

写 `A2A/inbox/task_<task_ref>_<YYYYMMDD_HHMMSS>.json`（同目录 `.tmp` 再 `os.replace`）。

**worker 取正文的顺序**：`instruction` → `prompt` → `question` → `note` → `description` → `title` → `task_book` 文件 → 原始 JSON 重读。全空则回 `BLOCKED` 并把任务移 `processed/`（不会死循环）。所以派活**必写 `instruction`**。

### 6.4 回执与结果

- 回执：`outbox/receipt_<task_ref>_octop_<YYYYMMDDTHHMMSS>.json`，字段 `receipt_id`/`task_ref`/`from:octop`/`to:<原 from>`/`ts`/`status`/`note`/`result_file`/`acceptance`。
  `acceptance` = `{p, pass, why, mode}`，观察模式验收结果，**不改 `status`**；样本矩阵与升硬拦的判据见 `a2a-file-bus` → `references/delivery-acceptance.md`。
- 正文：`results/result_<task_ref>_octop_<ts>.md`（问题 + 回答 + 专家 id + 耗时）。
- **群转发摘要行**：worker 处理完追加一行，守护只 `grep` 这一行转管理群，格式固定：
  `【OCTOP:<agent_id>】<status> <结论前 120 字>｜<result_file 或 ->｜<result_file 的 sha256 前 8 位>`
  保留 sha256 前 8 位是为了让收单方能拿摘要反查原件、确认没被改。改了这行格式等于改掉守护的抓取条件，两处必须同改。
- 任务：处理完 `shutil.move` 到 `processed/`。

### 6.5 五个必知行为

1. **幂等靠 `already_done()`**：扫 `outbox/` + `processed/` 找 `receipt_<task_ref>_octop*`，有则跳过。同步桥会把 `processed/` 里的任务**重新同步回 `inbox/`**，所以同一个 `task_ref` 会在 inbox 反复出现——幂等检查是必需的，不是可选项。
2. **锁文件 `/opt/data/cache/scratch/.octop_a2a.lock`**：600s 内重复触发直接 `SKIP locked`，防 cron 重叠。异常退出会留锁，`finally` 里已 `unlink`，仍要会手动删。
3. **`--quiet` 与 cron 投递**：`no_agent` 模式**空 stdout 不推送**。worker 在 quiet 下只在真处理了任务时才 print，否则全静默——别把 `IDLE`/`SKIP dup` 打到 stdout，会每 3 分钟刷一条飞书。
4. **单轮上限 `MAX_PER_RUN = 3`**：每个任务最长等 `WS_BUDGET=240s`，三个满额就 12 分钟，超过 3 分钟周期——靠锁文件挡重叠，不要调大。
5. **worker 派活要自己拼输出格式后缀，不然每条交付都带英文思维链。** 任务正文是原样传给 `ws_chat` 的，§1 那句「直接给最终答案，不要输出思考过程」只对 CLI 提问生效，worker 不会自动加——于是模型把 `Let me search…` / `This smells like a hallucination trap` 这类思考过程一起写进交付正文，结果 MD 和回执 `note` 都变成半成品（实测 1,148 字回答里一半是英文思考）。在 `task_instruction()` 之后、调 `ws_chat` 之前拼上后缀。

   **三层防护，从治本到兜底**（`octop_a2a_worker.py` 已全部落地）：

   | 层 | 手段 | 作用 | 局限 |
   |---|---|---|---|
   | 1 | `OUTPUT_RULE` 常量追加到任务末尾 | 请求模型只输出结论 | 只是请求，模型不一定听 |
   | 2 | `_clean_answer()` 事后清洗 | 剥掉残留草稿行 | 会误伤，靠保护规则兜 |
   | 3 | 验收口径把「含思考过程」判不合格 | 让 p 反映真实质量 | 只影响分数，不改交付 |

   ⚠️ 加后缀仍会残留，根因是 `ws_chat` 把 `reasoning` 帧当正文拼接（见 §1）；要彻底干净得在帧过滤里跳过 `reasoning`，否则只能靠第 2 层兜。**根因修不掉时别假装修掉了**——Octop 专家的 `system_prompt` 是 `null`、容器内 grep 不到可写入口，`OUTPUT_RULE` 只是请求，交付时要说清「缓解」而不是「根治」。

   **`_clean_answer()` 四条规则**（顺序即代码顺序，缺一条就漏）：

   1. **全文中文 < 10 字 → 原样返回。** 否则英文报告、纯代码脚本会被删空。
   2. 剥 `Answer:` / `答案：` / `答案:` 之前的内容（仅当断点在前 200 字且前面无中文）。
   3. **逐行丢草稿，不能只看开头和末尾**——英文草稿会夹在正文**中间**（实测 414 字回答里夹着两句 `One sentence conclusion. Do not include disclaimer?`）。保留条件：空行 / 含中文 / 结构行（`|` `#` 三反引号 `>` 开头，或含 ≥2 个 `|`）/ 缩进行（4 空格或 Tab，代码块内容）。
   4. **行内英文前缀也要逐行剥**：`Note rate: 2026-10-21 ... **结论：...**` 这种混行剥到第一个汉字，但回退到最近的 Markdown 标记（`**` / 反引号 / `[`），且前缀 ≤120 字符、不以 `#|->*` 开头。

   ⚠️ **「这一行有没有中文」不能当判据**：英文行里夹一个 `"价格指数"` 就会被判成中文行而漏剥。用**汉字占比 ≥15% 且 ≥3 个汉字**。
   ⚠️ 保留英文业务术语（`ceny-i-akcii`、`EAC`、`TR CU`、`CoC`）是正确行为，别当成没洗干净。
   ⚠️ 这种交付被自动验收判成低分是**判对了**，不是误判——不要靠调阈值把分糊上去。

### 6.6 端到端验收

```bash
# 1) 投一个任务
# 2) 等 ≤ 一个 cron 周期，看 processed 出现 + outbox 有回执
ls /opt/nas/volume2/2-AI/A2A/processed | grep <task_ref>
cat /opt/nas/volume2/2-AI/A2A/outbox/receipt_<task_ref>_octop_*.json
# 3) 看 cron 实际输出（比等飞书快）
ls -1t /opt/data/cron/output/f96e2da0aa99 | head -1
```

只看到 `RUN` 不算完成，**必须看到 `DONE` + `result_file` 文件真实存在**。

## 6.7 飞书 channel：扫码一键建应用（2026-10-26 实测跑通）

Octop 自带飞书官方「扫码创建应用」（`lark_oapi.register_app` 设备授权流，RFC 8628），**不需要人去开放平台手建应用**。

### 流程

```bash
# 1) 容器内拉起创建器（前台会阻塞等扫码，用 -d + 日志）
sudo -n docker exec -d octop sh -c 'cd /app && /app/.venv/bin/python3 -m octop.infra.gateway.bot_creators.feishu_bot_creator create > /tmp/feishu_creator.log 2>&1'
# 2) 取二维码 URL（JSON 行里的 show_qrcode 事件）
sudo -n docker exec octop sh -c 'cat /tmp/feishu_creator.log'
# 3) 把 content.url 渲成 PNG 给 BOSS 扫（终端 ASCII 图 BOSS 扫不了）
#    segno.make(url).save('qr.png', scale=12, border=4)
# 4) BOSS 扫码确认后，finish 事件里给 app_id / app_secret / bot open_id
# 5) 绑到 agent（main = 小通·通用助手）
POST /api/agents/{aid}/channels  {"kind":"feishu","name":"feishu","config":{"app_id":...,"app_secret":...,"enabled":true}}
```

**验收硬指标**：① POST 回 201 且 `runtime.connected=true`；② `docker logs octop | grep Lark` 出现
`[Lark] connected to wss://msg-frontier.feishu.cn/ws/v2`（这就是事件订阅长连接，无需再配 webhook）。

### 坑

1. **`oct_lib.call()` 返回 `(status, data)` 元组**，不是 dict——直接 `.get('data')` 会 AttributeError。而且 `data` **不一定是 dict**：`GET /api/agents` 返回的是 list，`json.loads(body)` 与 `body.get()` 一样会炸。固定写法 `code, items = O.call("GET", path, tok, None)`，再按 `isinstance` 分支。
2. **channel 回读 `config` 是 `{}`**：服务端脱敏，不代表没写进去；判据看 `runtime.connected`。
3. **channel 建立前发来的消息收不到**：建 channel 之前 BOSS 在私聊里说的话不会补投，必须让他重发一条验收。
4. **二维码有效期 `expire_in` 实测 3600s**，别急着催；但进程必须一直挂着，进程死 = 码作废。
5. **别转发别人抓的旧码**：设备授权码一次性，过期扫不动；每次自己重跑创建器拿新的。
6. `feishu_bot_creator` 的 stdout 是**逐行 JSON**，`show_qrcode` 的 `content` 本身是**转义过的 JSON 字符串**，要二次 `json.loads`。
7. 凭据落 `/opt/data/secrets/octop_feishu_app.json`（600），**不要写进 argv**（ps 可见）。

## 6.8 群内直触发（不写 JSON 派活）

业务节点不想碰总线文件时，让它在群里发一行 `octop:<别名> <问题>`：

```bash
/opt/data/bin/octop_grp.py "octop:小定 用一句话说明你能帮店群线算什么"
```

- 正则 `octop[:：]\s*(\S+)\s+(.+)`，中英文冒号都吃；别名走与 worker 同一张 `ALIAS`。
- 结果落 `A2A/results/result_GRP-<ts>_octop_<ts>.md`，并在群里回 `【OCTOP:CODE】…` 一行。
- 实测一次全链约 40s（小模型 + 无 RAG）。

⚠️ **现形态是「小卡读到群消息 → 跑脚本」，不是独立 bot 监听**：要 7×24 无人值守必须另起常驻监听进程（读飞书长连接事件），否则小卡不在线就没人解析。交付时说清是哪一种，别让人以为已经能自动接话。

```bash
/opt/data/bin/octop health          # ok:true, agents_running>0
/opt/data/bin/octop ls              # 9 个 agent 全 running
/opt/data/bin/octop kb              # 蜂群知识库 docs 数
curl -s http://192.168.199.2:8088/api/health
ssh DY@192.168.199.2 'sudo -n docker inspect octop --format "{{.Config.Image}} {{.State.Status}}"'
```

KB 验收要落到「`ready == total`」而不是「已上传 N 篇」——上传只是进队列。
