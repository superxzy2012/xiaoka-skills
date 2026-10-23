---
name: unified-llm-gateway
description: Use when 用/改/排障 NAS 统一模型网关 c2atools(8321)。
---

# 统一模型网关 c2atools（NAS 8321）

BOSS 需求原话：**「无论走哪个模型，都能调用工具，都不会封号，或者报错」**。

🔴 **BOSS 划定范围（2026-10-23）**：网关 = **AFS(chat2api) + Flask 工具层 + Trim**，**只一个出口**。OmniRoute / CLIProxyAPI **不得**作为上游或兜底。`GW_UPSTREAMS` 默认 `c2a`，`FALLBACK_MODELS` 只允许写 AFS 内部模型名。

## 拓扑（当前形态）

```
Claude Code / 飞书 / 任意客户端
        ▼  http://192.168.199.2:8321
   c2atools (Flask, 容器内 8081)  ← Trim + 协议转换 + nudge + 串行闸门/退避
        ▼  c2a/<model>
   http://chat2api:8081/v1   （socat → 127.0.0.1:8080，AFS 1.6.0 网页 Cookie）
```

- `omni/` `cli/` 定义保留但默认不启用；要临时混入：`GW_UPSTREAMS=c2a,omni`。

**端口对照（BOSS 反复问「8081 那个 Flask 网关还在吗」，按这张表答）**：

| 入口 | 实际位置 | 说明 |
|---|---|---|
| **宿主 8321** | c2atools 容器内 8081 | ✅ 唯一对外网关入口，全部护栏/Trim/协议转换都在这里 |
| chat2api 容器内 8081 | socat → `127.0.0.1:8080` | 只是容器间中继，不是 Flask |
| AFS 原生 8080 | chat2api 容器内 | 裸上游，无 Trim/无护栏/无转换 |
| 宿主 8320 → 8080 | compose 端口映射 | **旁路，别给客户端用**（会绕过全部护栏） |

两个「8081」分属不同容器、不同网络（`c2a-net` 隔离），互不冲突；Mac 时代 Flask 直接占 8081，迁到 NAS 后宿主改叫 8321。

- 双协议：OpenAI `/v1/chat/completions` + Anthropic `/v1/messages`（流式与非流式都通）。
- `/health` 返回各上游 base/max_conc/min_interval；`/stats` 返回 `stats{c2a:{req,ok,err,retry,throttle_s}}` + `fail_counts{model:n}` + `pool_score{model:score}`（`/metrics` 是 404，别试）。`throttle_s` 与 `[throttle] ... 退避 Xs` 日志是「防封真的在工作」的取证依据，回答封号问题先拉这两个。
- **判断某供应商能不能用，看 `data.json` 的 `accounts`，不要看 `/v1/models`** —— models 只是映射表，没有账号照样列出来。容器内跑 `scripts/afs_accounts_probe.py`（打印 providerId / 凭据类型 / 过期剩余，不打印任何 token）。曾据此发现「DeepSeek 系列 6 个模型名全在，但 0 个 DeepSeek 账户，实际只有 3 个 GLM」—— 这类「模型名存在 ≠ 能调用」的错觉是 BOSS 提问的主要来源。
- 响应体 `model` 回显**真正答话的模型**；响应头 `X-GW-Model` / `X-GW-Upstream` / `X-GW-Fallback: 1`（仅非流式路径带）。

## 防封：限流节流（真防封）与请求瘦身（间接）是两件事

BOSS 的原始需求里「不会封号」和「能调工具」是两条独立目标，改代码时别混。

### 真防封（控频率：`_Gate` / `_backoff_sleep` / 动态评分）

| 机制 | 实现 | 参数 |
|---|---|---|
| 串行闸门 | `_Gate`：`Semaphore(max_conc)` + `next_at` 排程 | `C2A_MAX_CONC=1` / `C2A_MIN_INTERVAL=2.5`（omni 0.3） |
| 节奏抖动 | 仅在需要等待时叠加 `random.uniform(0, min(0.5, interval*0.25))` | 2.5s 档 → 实际 2.5~3.1s，防「每 2.5 秒一次」的机器人指纹 |
| 指数退避 | `_backoff_sleep`：`min(30, 2**min(attempt+1,4)) + uniform(0,0.8)` | 2→4→8→16s，封顶 30s |
| 熔断降权 | `pool_score` 1.0 起，失败 −0.5（下限 0.1），成功 +0.2（上限 3.0） | 弱模型自动退出轮换 |
| 诚实失败 | 静默空返回重试 2 次 → `502 upstream_unavailable` | 不在风控期硬怼 |

**容量边界（回答「会不会封号」必须主动给这个数）**：2.5s/次、全天不停 = **34,560 次/天**，任何网页端都会封。真要把某网页账号当主力，必须再加两道闸 —— ① 日配额上限（跑满返回 429 让上层换模型）；② 多账号轮换（单号日均压到几百次）。这两项**尚未实现**，别对 BOSS 说「封号问题已彻底解决」；准确口径是「机制就绪 + 当前未跑该供应商」。

### 请求瘦身（降体积，不是防封）

| 机制 | 位置 | 作用 |
|---|---|---|
| 工具定义 Trim `_compact_tools` | app.py | 29,825 B → ~4.6 KB；解决上游截断/选错工具/超时，**不控 QPS、不控并发** |
| nudge 系统提示 | app.py | 工具调用率 5/8 → 8/8 |
| `_flatten_content` | app.py | 修 content 块数组被 `str()`，Claude Code 的 tool_result 必需 |
| 上游内兜底 `FALLBACK_MODELS` | 只写 AFS 模型名（如 `GLM-5.3-thinking`） | 同一上游内换模型；**绝不跨到 omni/cli**（BOSS 边界） |

BOSS 容易把 Trim 记成防封手段 —— 主动讲清：Trim 管单请求体积，防封管单位时间次数，两套独立实现，不要含糊成「Trim 也防封」。

## 文件与部署

| 项 | 位置 |
|---|---|
| 源码（本地） | `/opt/data/cache/scratch/c2atools/app.py` |
| 生成器 | `make_c2atools.py`（首版）→ `upgrade_gw.py`（叠加统一网关补丁） |
| NAS | `DY@192.168.199.2:~/c2atools/{app.py,.env,Dockerfile,docker-compose.yml}` |
| 容器 | `c2atools`，`8321:8081`，网络 `default + c2a-net` |
| 备份 | `app.py.bak-prev`；改前一律先 `cp` |

**改完必须走这套同步 + 重建**：

```bash
cd /opt/data/cache/scratch/c2atools && tar czf /tmp/c2at.tgz app.py .env Dockerfile docker-compose.yml
B=$(base64 -w0 /tmp/c2at.tgz)
SSH="ssh -i /opt/data/.ssh/id_ed25519 -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 DY@192.168.199.2"
echo "$B" | $SSH 'base64 -d > /tmp/c2at.tgz && cd ~/c2atools && tar xzf /tmp/c2at.tgz && chmod 600 .env && md5sum app.py'
$SSH 'cd ~/c2atools && nohup sudo -n docker compose up -d --build > /tmp/c2at_build.log 2>&1 &'
```

## 验收（改完必跑）

```bash
curl -s -m 8 http://192.168.199.2:8321/health          # 应只有一条 upstream: c2a
curl -s -m 8 http://192.168.199.2:8321/v1/models       # 应全是 c2a/* 前缀
curl -s -m 60 -X POST http://192.168.199.2:8321/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"c2a/GLM-5.3","messages":[{"role":"user","content":"在线?"}]}'
```

**验收必须包含一条「故意打不通」的用例**：把上游模型名写错或临时停 chat2api，确认返回的是 JSON `502 {"error":{"type":"upstream_unavailable"...}}`，**不是 Flask 的 HTML 500 traceback**。异常路径没人走过就会藏着 `NameError`（`_handle_sync` 里引用只在 `_call_with_chain` 内定义的局部变量，曾把干净的 502 变成 HTML 500）。

- 完整验收：`/opt/data/cache/scratch/gw_accept.py`（双协议 + 12 个胖工具测 Trim + 降级 + 限速），需先 `docker cp` 进容器（重建会清 `/tmp`）。
- 流式 + 工具：`gw_stream_test.py` — Anthropic SSE 应见 `content_block_start/tool_use` + `message_stop`；OpenAI SSE 应见 `delta.tool_calls` 且 arguments 完整。
- 实测基线（2026-10-23）：Anthropic 流式 + 工具 1.3s、OpenAI 流式 + 工具 1.7s，均 200。

## 幽灵工具调用（2026-10-23 已修，别再踩）

**现象**：客户端**不带 tools** 的普通对话，上游返回 `200` 但 `content` 为空、`tool_calls` 里凭空多一个 `finish`（`arguments={}`）。带 tools 的请求反而正常。

**根因**：AFS 的 toolParser 在没有 tools 时也会尝试解析「结束标记」，把收尾动作误判成一次工具调用，正文被整段吞掉。

**修法（app.py 里已成套，别拆）**：
1. `_ensure_tools(payload)` —— 出口层无条件保证 `tools` 非空，客户端没给就注入哑工具 `gw_noop`。
2. `_strip_phantom(data)` —— 回包剔除 `finish`/`gw_noop`，非流式在 `_post()` 里做，流式在 `_aggregate_stream` 聚合后做，SSE 逐块过滤（`_phantom_idx`）。
3. `_with_guard(messages, tools)` —— 在消息最前面钉一条「只能使用下列工具，禁止声称拥有 open/open_url/web_search」的系统提示。AFS 会给模型塞自己的 system prompt（“你是本地编码智能体，可用 open_url”），不钉护栏模型会反复调用不存在的 `open`，最后以道歉收尾。

**验收基线（2026-10-23 修复后实测）**：
| 用例 | 结果 |
|---|---|
| 纯文本 ×4（无 tools） | 200，全部有正文 |
| 纯文本流式 | 200，正文完整 |
| Anthropic 纯文本 | 200，`stop_reason=end_turn` |
| OpenAI 非流/流 + 工具 | 200 / 1.7s、3.3s，`get_weather` 参数正确 |
| Anthropic 非流/流 + 工具 | 200 / 0.9s、4.6s，`tool_use` 正常 |
| 多轮工具闭环（tool_result → 最终文本） | 200，第二轮不再重复调工具 |
| Trim：12 个胖工具 29,498 B | 200 / 5.5s，选中正确工具 |

## 客户端接入

- **Claude Code（容器 claude-code-nas）保持直连 `http://192.168.199.2:20128`**。2026-10-23 实测把它切到 8321 后**重工具任务全废**：CC 这一版是「延迟工具发现」架构（工具表里是 `DeferredToolPlaceholder` / `ToolSearch`，13 个工具 + 巨长 system prompt），GLM-5.3 网页版读不懂，反复调不存在的 `open` 工具，8 次上限耗尽后以道歉收尾（`/workspace` 里根本没落文件）；同一模型配单个工具定义时 1.7s 就调对。→ **结论：网关适合轻量/标准工具调用（≤5 个工具、schema 简单），不适合当 Claude Code 的后端**。已回滚，备份 `docker-compose.yml.bak-omni`。
- **AFS「模型管理 → 工具调用」页对 Claude 无用（2026-10-23 实测）**：客户端类型下拉只有两项 —— `Standard OpenAI Tools` 与 `Cherry Studio MCP`，**没有 Claude 项**。这层管的是「网页模型怎么被喂工具」（面向 OpenAI 兼容客户端），Claude Code 走 Anthropic `/v1/messages`，不经过它；网关已做协议转换，所以协议也不是障碍。
- **工具数量阈值（同一 CC、同一 prompt、只换后端对照）**：`--tools "Bash"` ✅ 落盘；`--tools "Bash,Read"` ✅ 落盘；`--tools "Bash,Write"` ❌ 8 轮耗尽后道歉；`--tools "Bash,Read,Write"` ❌ 同样失败；**同一 4 工具集走 20128 ✅ 立刻落盘**。→ 故障点在 GLM-5.3 网页版对多工具表的理解能力，不在 CC、不在网关协议。含 `Write` 时尤其容易触发「执念调不存在的 open」。
- **「运行测试」（冒烟测试）是 1.6.0 半成品，失败不代表工具能力有问题（2026-10-23 源码级定位）**：① 前端 `preload` 把管理 API 写成 `127.0.0.1:19825`，但服务端 managementRoutes 实际挂在**代理端口 8080 的 `/v0/management/`** 下，19825 从不监听 → `runSmoke` 必失败；② 即使调通，`POST /v0/management/tool-calling/smoke` **只生成 fixture 并固定返回 `success:true, category:"pass"`**，message 原文就是「Send it through /v1/chat/completions with a mapped model to run a live provider smoke」——它根本不做真实调用；③ fixture 的 `model:"tool-smoke-test"` 默认无映射。真实冒烟要自己拿 fixture 打 `/v1/chat/completions`。
- **Cherry 模式的真实表现（同一 fixture、model 换 GLM-5.3-thinking）**：AFS 原生 8080 直打 —— `tool_choice:"auto"` ✅ PASS（1.9s，`weather-test:get_weather{"city":"Hangzhou"}`）；`tool_choice` 强制指定带冒号工具名 ❌ FAIL（0.5s、content 空）—— 这是幽灵工具 bug 的另一面。同一请求经网关 8321（guard+幽灵修补）→ ✅ PASS 4.5s。结论：cherry 形态**只有套网关能用**。
- **`autoStartProxy` 默认 false 是运维地雷**：容器重启后 8080 不自启 → 网关全 502，且 UI 语言会回到英文。部署时务必把 `config.autoStartProxy` 置 true（改 `data16/data.json`，改完必须重启容器才生效；容器内 `ss` 可能不存在，用 `curl 127.0.0.1:8080/health` 判活）。
  - 切到网关时模型名要跟着换前缀：`c2a/GLM-5.3`；切回 20128 时才是 `naswb/...` / `a2a/...`。
- 任意 OpenAI 客户端：`base_url=http://192.168.199.2:8321/v1`。
- 内网无鉴权；需要时再加。

## 坑（都踩过）

0. **改 asar / 账户数据必须用 volume 挂载，不能用 `docker cp`** —— `docker compose up -d` 重建容器会把 `docker cp` 进去的东西全部还原成镜像内容。曾经「1.6.0 升级成功」是假象：容器重建后又变回 1.4.0（无 `GLM-5.3`），所有 GLM 调用 200 空正文。正确姿势：
   - `- ./asar16/app.asar:/app/electron/resources/app.asar:ro`（1.6.0，md5 `6aaa2bc8ce28997b639262d37ea79838`）
   - `- ./data16:/root/.chat2api`（**1.6.0 的账户库在 `/root/.chat2api/data.json`**，1.4.0 在 `/root/.config/chat2api`；不挂就每次重建丢账户）
   - 校验：容器内 `md5sum /app/electron/resources/app.asar` 必须等于上面那串，且 `data.count(b"GLM-5.3")>0`。
1. **`c2a-net` 必须在 compose 里声明 `external: true`**，否则重建掉网 → `c2a/` 前缀全 `ConnectionError`。
2. **chat2api 容器内要 `socat 8081→127.0.0.1:8080`**，写在挂载的 `start.sh`（`./start.sh:/app/start.sh:ro`）里，否则每次重建丢中继。
3. **容器重建清空 `/tmp`** → 验收脚本要重新 `docker cp`。
4. **NAS docker 一律 `sudo -n docker`**（DY 无 docker 组权限）。
5. **任何含引号/花括号的远端命令都别内联进 `ssh '...'`** —— `docker exec ... socat`、`docker ps --format "{{.Names}} | {{.Ports}}"` 这类一律报 `unexpected EOF while looking for matching "`，白丢两轮。固定套路：本地 `write_file` 写 `.sh`/`.py` → `base64 -w0 | ssh 'base64 -d > /tmp/x'` → `ssh 'bash /tmp/x'`（或 `docker cp` 后 exec）。只有纯单引号、无嵌套、无 `{}` 时才内联安全。
6. **NAS 家目录是 `/home/DY`**，不是 `/root`。
7. **terminal 输出常被截断成「1 lines」** → 结果落盘 + `base64 -w0` 拉回本地解码，或 `read_file`。
8. **GLM 200 空正文有两条完全不同的根因，先分诊再动手**：① **幽灵工具 bug（已修）** —— 上游把收尾动作误判成工具调用、正文被整段吞，特征是「带 tools 正常、不带 tools 空」；`_ensure_tools`/`_strip_phantom` 已兜住，实测 GLM-5.3-thinking 正常出正文（1.9s）。② **账户没有真人网页会话** —— 只填 `chatglm_refresh_token` 能「添加成功 / 1-1 在线」，但调 chat 一律空返回；chatglm.cn 登录前有滑块验证（`Please slide to verify`），必须真人在浏览器过滑块 + 扫码。判据：先看是否「不带 tools 才空」（→ ①，同时查 asar md5 是否被重建冲回旧版），再跑 `scripts/afs_accounts_probe.py` 看凭据类型（只有 refresh_token、无真人会话痕迹 = ②）。
   → 修法：跑 `scripts/afs_open_login.py`（自动走「供应商 → 添加账户 → 下一步 → OAuth 登录 tab → 打开 OAuth 登录」，把 chatglm 页停在滑块前），然后让 BOSS 在 noVNC `http://192.168.199.2:6080` 过滑块 + 扫码。
   → 自检命令：`curl -s http://192.168.199.2:8321/v1/models`（应只列 `c2a/*`）+ 发一条 `c2a/GLM-5.3` 看是否有正文。
9. **noVNC 6080 显示目录列表 = 容器重建把 `index.html` 软链冲掉了**。websockify 的 `--web=/usr/share/novnc` 没有默认首页就退化成目录索引。修法：`ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html`，并且**把这行写进挂载的 `start.sh`**（放在 `websockify` 那行之前），否则下次重建再犯。校验：`curl -s http://192.168.199.2:6080/ | head -c 100` 应出现 `noVNC_loading`。
10. **Electron/React 里的 Tab 切换别用 `get_by_text(x).evaluate("e=>e.click()")`** —— 文字命中的是内层 span，事件不冒泡到 Tab，页面看起来「点了没反应」。用坐标点：先 `getBoundingClientRect()` 取中心，再 `pg.mouse.click(x, y)`。输入框同理（`locator.fill()` 对受控组件无效）：`e.focus()` + `pg.keyboard.insert_text()`。
11. **判内核版本看容器内 asar 的 md5，不要看 UI 显示** —— UI 模型列表是渲染结果，`docker cp` 进去的 asar 被重建冲掉后，UI 仍可能显示旧列表。排查任何「模型不存在 / 返回空」之前先 `md5sum /app/electron/resources/app.asar`。
12. 网页刷新令牌接口 `POST https://chatglm.cn/chatglm/user-api/user/refresh`，必须带 `Authorization: Bearer <refresh_token>` + `X-Device-Id`/`X-Nonce`(sign3)，裸调返回 `40001 bad request` —— 别用「curl 刷新成功」当 token 有效判据。
13. **AFS 脚本中心「检查构建产物」报 `Cannot find module '/app/electron/resources/scripts/check-source-artifacts.js'`** —— 这是开发期产物检查脚本，运行时容器里根本没有 `scripts/` 目录。修法：在挂载的 `start.sh` 里补一行（在 `websockify` 之前）`mkdir -p /app/electron/resources/scripts; [ -f .../check-source-artifacts.js ] || echo 'console.log("...skipped in runtime container");' > .../check-source-artifacts.js`，让它跑成 no-op。注意 start.sh 里嵌 `echo` 引号要用单引号包，否则 `bash -n` 语法错。

## 防封配额层（2026-10-23 交付）

### 为什么不能用 AFS 自带的 `dailyLimit`
反编译 1.6.0 的 `out/main/index.js`：`LoadBalancer.resetDailyUsage()` **全文只定义、零调用点**，没有 `setInterval`、没有午夜定时器。`account.todayUsed` 只增不减 → 一旦设 `dailyLimit`，用完那天账号就**永久锁死**，只能手改 `data.json` 才能救。所以日配额必须在 Flask 层做。

### 网关侧实现（`c2atools/app.py`）
| 组件 | 作用 |
|---|---|
| `_family_of(model)` | 模型名 → 族（deepseek/kimi/mimo/minimax/qwen/glm/other），顺序敏感：先具体后宽泛 |
| `QUOTA_RULES` | 族 → (每日上限, 最小间隔秒)。deepseek 300/8s、kimi·mimo·minimax 400/6s、qwen 600/4s、glm 1200/2.5s |
| `_FAMILY_GATES` | 每族独立 `_Gate`（并发 1 + 最小间隔），比全局 `MIN_INTERVAL=2.5s` 更严 |
| `_quota_check` / `_quota_usage` / `_quota_reset` | 计数、查询、重置；北京时间 0 点自动换日 |
| 持久化 | `QUOTA_FILE=/app/data/quota.json` + compose 卷 `./data:/app/data` → 容器重建不清零 |
| 超限 | OpenAI 通道 429 `daily_quota_exceeded`；Anthropic 通道 429 `rate_limit_error`，body 都带 `quota{family,used,limit,reset_at}` |
| 端点 | `GET /quota`（当日各族用量）、`POST /quota/reset?family=`（手动清零） |
| 环境变量 | `Q_<FAMILY>_DAILY` / `Q_<FAMILY>_INTERVAL` 覆盖默认值，`GW_QUOTA_ENABLED=0` 可整体关 |

**网页端失败零重试**：`_request` 里 `_retries = 0 if _fam in ('deepseek','kimi','mimo')`，静默空返回的 `_retry_budget` 同样归零。1 次失败重试 3 次 = 把 1 次可疑请求放大成 4 次，是封号最快的路径。宁可让上层收 502 换模型。

### AFS 侧配套
`loadBalanceStrategy='round-robin'` + `retryCount=1`（原 3，网页端失败放大）。改 `data.json` 的**正确顺序**：`docker stop` → 改文件 → `docker start`。直接 `docker restart` 会让运行中的 AFS 在退出时把内存配置写回磁盘，覆盖你的修改（实测 retryCount 改完变回 3）。

### 踩过的坑
- **`docker stop` → `docker start` 后容器无限重启，日志 `Missing X server or $DISPLAY`**：`/tmp/.X99-lock` 残留，Xvfb 起不来 → Electron 退出。修法：`start.sh` 里 `Xvfb :99` 那行**之前**插 `rm -f /tmp/.X99-lock /tmp/.X11-unix/X99`。`docker restart` 不触发（进程正常退出会清理），只有 stop/start 会。
- **Anthropic 通道配额双扣**：`/v1/messages` 的 `_a_call_pipeline` 是 `app.test_request_context` 里直接调 `chat_completions()`，两处都写 `_quota_check` 就会 1 次请求扣 2 次。只在 `chat_completions` 扣，`anthropic_messages` 透传内层 429。
- **`UNDERLYING_MODEL` 默认值是 `deepseek-chat`**：`.env` 没设 `UPSTREAM_MODEL` 时，所有 `claude-*` 请求都被映射到 deepseek → 没有 DeepSeek 账号时 Anthropic 通道全 502。必须显式设 `UPSTREAM_MODEL=GLM-5.3-thinking`。

### 验收脚本（都在 `/opt/data/cache/scratch/`）
- `test_quota.py`（容器内跑）：族识别 11 例 + 扣减/超限/重置，29 项断言
- `verify_quota.py`（宿主跑）：`/health.quota` → `/quota` → 真实 GLM 请求计数 +1 → Anthropic 通道计数 +1 → `/quota/reset`
- `test_429_live.sh`：临时 `Q_DEEPSEEK_DAILY=0` 重建 → 两通道各打一次应 429、GLM 不受影响 → 恢复配置
- `post_login_setup.py` / `apply_afs_cfg.py`：AFS 账号体检与配置修正（登号后跑）
