---
name: grok-feishu-bot
description: 飞书 Grok/muse 机器人运维（双桥+grok2api/muse2api+云端派单）。
---

# 飞书 Grok 机器人（grok2api 全链路）

BOSS 自建：飞书里直连 xAI Grok 4.5，走免费 xAI 账号网页会话逆向，**不是官方 API、不扣费**，但受免费号每小时额度限制。

## 架构（三层，全在绿联 NAS 192.168.199.2）

```
飞书「Grok 机器人」(app cli_aa6a7f9bda78dd02)
  ↕ 长连接 WebSocket（免公网回调）
grok-feishu-bridge 容器 (host 网络, 镜像 grok-feishu-bridge:latest)
  ├─ server.js  飞书消息 ↔ OpenAI 格式；收图/画图回传/模型切换指令
  └─ worker.js  A2A 文件总线 worker（to=grok，60s 轮询）
  ↓ HTTP
192.168.199.2:45080  grok2api（跑在 hermes 容器内 /opt/data/services/grok2api）
  ↓ 美国出口必须洛杉矶
host: mihomo2 7894（NCINK）→ grok.com
```

## 关键路径

- grok2api 代码/启动：hermes 容器内 `/opt/data/services/grok2api/`（server.py, run.sh, .env, accounts.txt 登录态, g2o.log）。端口 45080 由 hermes 容器 compose `/volume2/hermes/docker-compose.yaml` 发布（加端口映射后需 compose 重建容器，grok2api 不会自动起）。
- 飞书桥源码+部署：宿主 `/home/DY/grok-feishu/{server.js,worker.js,Dockerfile,docker-compose.yml,.env(600)}`（SFTP 视角是 `/home/grok-feishu/`，因为 SFTP 根把 `/home` 映射到系统 `/home/DY`）。
- A2A 卷：compose 挂 `/volume2/2-AI/A2A:/a2a`。worker 只处理 `to` ∈ {grok,grokbot,grok-bot,格罗克}。
- 凭证：飞书 App Secret 在 `/opt/data/services/grok2api/feishu_app.env`(600) 和宿主 `/home/DY/grok-feishu/.env`(600)，**不外发**。
- SSH：用别名 `nas-ugreen`（DY 账号，已配公钥免密）。docker 命令 `sudo -n docker` 免密；但 `sudo -n ls/cat` 等非 docker 命令**要密码**，别用。

## 模型

grok-fast / grok-auto / grok-expert / grok-heavy(A2A 默认) / grok-build。
飞书会话内指令：`/fast /auto /expert /heavy /build` 切档，`/model` 查询，`帮助` 看说明。

🔴 **飞书默认必须是 `grok-fast`，不能是 `grok-auto`。** 免费额度按档位分，差一个数量级：

| 档位 | 实际模型 | 免费额度 |
|---|---|---|
| `grok-fast` | Grok-3 Turbo | 10-12 条 / 2 小时（滚动窗口） |
| `grok-auto` | 遇复杂问题自动升 Grok-4 | **5 条 / 12 小时** |
| `grok-expert` | Grok-4 | 5 条 / 12 小时 |
| `grok-heavy` | Grok-4 Heavy | 免费不可用 |

`grok-auto` 看着「智能」，实际一遇到需要推理的问题就升到 Grok-4，5 条打光后全线报额度，用户体感就是「怎么老提示额度」。日常问答 `grok-fast` 足够；真要深推理让用户 `/expert` 单次切过去。

**桥已内置 auto→fast 自动降级**：`handleGrokReply` 里若首选档命中 `usage limit|quota|rate` 且当前不是 `grok-fast`，自动重试一次 `grok-fast`，报错文案里带上实际用的档位。用户即使 `/auto` 撞了 Grok-4 的 5 条墙，也能立刻拿到答案而不是看到死路。

**会话档位存在内存 `chatModel` Map 里，重启桥即清空**（回到 `.env` 的 `GROK_MODEL`）。用户说「某个会话老提示额度」而全局默认已经是 `fast` 时，先怀疑该会话被 `/auto` 过——重启桥比逐会话发 `/fast` 快。

## 看门狗

grok2api 由 hermes cron 每 5 分钟巡检（`/opt/data/scripts/grok2api_watchdog.sh`，no_agent+deliver=local，零模型成本）。容器重建后必须确认 45080 活着。

**改看门狗前先确认 cron 到底调的是哪个文件。** `~/.hermes/scripts/`（本机即 `/opt/data/scripts/`）才是 cron `script` 字段的解析根；`/opt/data/services/grok2api/watchdog.sh` 那份同名文件**没有任何 job 引用它**，改它等于没改，下一轮故障照旧没人管。查法：`cron/jobs.json` 里找到该 job 的 `script` 字段，或 `cronjob_manage action=list` 看 `script`。判据不是「我改了个看门狗」，是**那个被调用的文件里包含新判据**。

**健康判据是 `available>0`，不是 `"ok":true`。** 实测出现过 `ok:true` 但 `available:0`：进程活着、端口通，但内部 statsig/session 状态坏了，上层表现为 `grok error (upstream): connect failed: ConnectionResetError`。只查 `ok:true` 的看门狗会认为健康而全程不作为。判据写 `ok:true && available>0`，连续 2 轮为 0 才重启（避免真·额度耗尽时反复重启空转），重启后等 **100s** 再验。

**但 `available:0` 本身不等于坏。** 它有两个来源：①账号撞 quota 后进入 `COOLDOWN_SECONDS`（默认 300s）冷却；②内部状态真坏。区分靠**实际发一次请求**：`curl -s -X POST http://127.0.0.1:45080/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"grok-fast","messages":[{"role":"user","content":"好"}]}'` —— 能回就只是冷却/空闲，别重启；报 ConnectionReset/SSL 才是真坏。

**也别把 `statsig_ready:false` 当故障。** 实测 `available:1`、请求 4 秒正常返回时它照样是 `false`——statsig 是旁路懒加载状态，只有「`available:0` **且** 实际请求失败」才说明进程坏了。同理，重启后 100s 内仍 `available:0` 时先发一次探活请求再判断，很多「重启没生效」其实是首次请求还没触发账号状态刷新。

🔴 **看门狗重启后的等待必须 ≥100s，别用 45s。** `available` 从 0 到 1 实测要 ~90 秒（statsig 初始化慢）；只等 45s 会把「正在预热」判成失败，日志里刷满 `restart FAILED`，而进程其实已经起来了——表现为看门狗每 5 分钟「杀掉→拉起→报失败」空转数小时，服务被反复中断。判据不是「日志说 FAILED」，是**探活请求能不能回**。

重启时**必须精确 kill**：`ps -eo pid,args | grep "[m] uvicorn server:app" | awk '{print $1}' | while read p; do kill $p; done`。用 `pkill -f "uvicorn server:app"` 会匹配到执行这条命令的 shell 自己，命令 exit -15、后续重启步骤全不执行。

三层诊断脚本：`scripts/grok2api_triage.py`（读 healthz + 直接拿 cookie 打 grok.com 轻量接口 + 三路代理稳定性对比），一次跑完就能区分「cookie 失效 / 额度耗尽 / 进程状态坏了」。

## 排障

- **quota / usage limit / rate**：撞顶后聊天/搜索/识图/画图全 502。**先查当前模型档**——额度按档分（见上表），`auto`/`expert` 只有 5 条/12 小时、`fast` 有 10-12 条/2 小时，多数情况是档位选错而不是账号废了。窗口是**滚动**的：第 1 条发出后满 2 小时那一条才回补，不是整点重置——所以突发连问最容易撞墙，摊开用几乎撞不到。真撞顶就等窗口滚动，或**加免费账号**（`accounts.txt` 每多一个账号就多一份 10-12 条/2h）：用 Gmail `+tag` 别名注册、走真实 Chrome（headless 被 Cloudflare 挡），注册到收码那步要 BOSS 把码发过来，完整配方见 `cdp-browser-automation` 的「新开隔离上下文」。新 cookie 追加后重启进程并实测一条真实 chat。A2A worker 遇 quota 回执置 **HOLD** 且不移除任务，下轮自动重试，不是 bug。
- **先分清是不是真 quota。** `ConnectionResetError` / `SSL: UNEXPECTED_EOF` 与额度无关：直接拿 `accounts.txt` 的 cookie 打 `GET https://grok.com/rest/app-chat/conversations?pageSize=1`，返回 200 就说明 cookie 有效、网络通，问题在 grok2api 进程状态，重启即可；返回 401 才是 cookie 失效；能通但发消息报 limit 才是真额度。别把三种混成一件事。
- **读 `accounts.txt` 别用 `MozillaCookieJar.load()`。** 该文件混着 `# Netscape HTTP Cookie File`、`account 1:`、空行等非 7 字段行，`load()` 抛 `ValueError: not enough values to unpack (expected 7, got 1)`。逐行 `split("\t")`，只取 `len(parts)==7 and parts[0].startswith(".")` 的行手工塞 `http.cookiejar.Cookie`。
- **画图只回 Image generated 无图**：grok 图在私有 assets.grok.com 或 imagine-public.x.ai。已改 server.py：无 freeimage key 时回落本地 `/img?u=` 认证代理端点（带账号 cookie + 浏览器指纹下载），两域都走它。免费号画图极易 WS timeout + 秒耗额度，实测不稳定；FREEIMAGE_API_KEY 未配。
- **改 server.py 不生效**：uvicorn 需重启。进程是 `uvicorn server:app`。注意 `pkill -f server:app` 会连执行 shell 一起 SIGTERM（exit -15），用 tracked background 跑 `cd /opt/data/services/grok2api && HTTP_PROXY=http://192.168.199.2:7894 HTTPS_PROXY=$HTTP_PROXY NO_PROXY=127.0.0.1,localhost ./run.sh`。
- **改桥代码**：本地改好 → `base64 -w0 server.js` 走 `ssh nas-ugreen "cat > /home/DY/grok-feishu/server.js.new"` 传（scp/sftp 被限）→ 远端 `base64 -d` 还原并核对字节数 → `sudo -n docker compose build && sudo -n docker compose up -d` → logs 确认 `ws client ready` + `[a2a] worker 启动`。
  - **改了代码里的默认值可能不生效，先看 `.env`。** compose 用 `env_file: .env`，`.env` 里的同名键会盖掉 `process.env.X || '默认值'`。两处都改，改完必须 `sudo -n docker exec <容器> printenv <KEY>` 验证容器内真实值——只看代码判断不了。
  - **`.env` 直接 `sed -i` 改，别加 sudo**：文件属主就是 SSH 用户；`sudo -n sed` 会因 sudoers 只放行 docker 而报 `a password is required`，静默失败后你会以为改过了。
- **`pkill -f <脚本名>` 会杀掉自己**：命令行里带着脚本名，`pkill -f` 匹配到执行这条命令的 shell 本身，命令返回 `exit -15`（SIGTERM），后续步骤全不执行。改用 `ps -eo pid,args | grep "[c]loud_worker.py" | awk '{print $1}' | while read p; do kill $p; done`——方括号让 grep 不匹配自己。
- **出口 Cloudflare 403**：必须走美国节点 7894 洛杉矶，香港/机房 IP 不行。
- **飞书收不到消息**：日志看 ws client ready；开放平台「事件与回调」选长连接并订阅 im.message.receive_v1（智能体应用一键创建已预置）。

## 云端任务（飞书派单 → Grok 云端跑 → 结果推回飞书）

Grok 网页端自带 **Automations**：云端按计划自主跑任务，免费账号**全功能开放**（Once/Hourly/Daily/Weekly/Monthly + Gmail/Outlook/GitHub 触发器，Notifications 可推 App/Email）。付费墙只在 **Grok Bot**（常驻助理），不在 Automations。别假设需要 SuperGrok。

```
飞书「云端 <任务>」/「每天9点 <任务>」
  ↓ 桥 server.js parseCloud() 写文件
/volume2/2-AI/A2A/cloud-tasks/inbox/CLOUD-*.json   （桥挂 /a2a，hermes 挂 /opt/nas/volume2）
  ↓ 3s 轮询
cloud_worker.py（hermes 容器内常驻，/opt/data/services/cloud-worker/）
  ↓ 页面内同源 fetch
https://grok.com/rest/*  →  结果  →  飞书 im/v1/messages 推回原 chat_id
```

接口全集与请求体字段见 `references/grok-automations-api.md`。

**必须遵守的四条：**

1. **走 REST，不点 DOM。** 建/跑/查/删/取正文全部有内部 REST 端点，在页面内 `fetch` 执行（cookie 已在 context 里）。点界面按钮会被遮罩、滚动、SPA 重渲染搞死，实测每次都要重写选择器。
2. **派单与等待解耦（异步 watch）。** 主循环只负责建任务+触发+登记 `state/watches.json` 就返回；另一个循环盯所有 watch 的 runs，出结果才推。在派单路径里同步 `while` 等结果会让一个慢任务堵死后面所有派单，而且超时后你会把任务删掉、永远拿不到真结果。
   - **只有终态才写进 `seen`。** run 刚建出来是 `PENDING`，若在 PENDING 阶段就把 `taskResultId` 记进 `seen`，`once` 任务会立刻被判完成并删除，答案永远推不出去。判据：日志里只有 `WATCH_DONE` 没有 `PUSH_OK` —— 这是最隐蔽的静默丢失，不要用「跑完了」当成功。
3. **chat_id 原样带回，绝不跨 app 猜。** 机器人只能往自己所在的会话发消息；拿别的 app 的 DM chat_id 发，飞书返回的是 **HTTP 400 Bad Request**（不是 99992361 那种明确报错，很容易误判成代码 bug）。派单时把收到消息的 `msg.chat_id` 写进任务文件。
4. **答案正文要二次取。** run 元数据只有 `conversationId`，正文在 `GET /rest/app-chat/conversations/{cid}/responses` 的 `responses[].message`（`sender==ASSISTANT`）。取回后用正则清掉 `<grok:render ...>...</grok:render>` 内部标签再推飞书。

**排队延迟是正常的：** `POST /run` 返回 200 后，云端要排队约 4 分钟才真正出结果（免费号）。把等待窗口设成分钟级、用 watch 表跨轮询持久化，别用 30~60 秒超时判失败。

**定时任务同样走 watch：** `daily` 只建 schedule 不触发，watch 常驻盯 runs，每次新 `taskResultId` 成功就推一次。立即任务（`once`）拿到结果后删任务+注销 watch；定时任务不删。

**凭证键名不统一：** grok 的 `feishu_app.env` 用 `FEISHU_GROK_APP_ID/SECRET`，muse 的用 `FEISHU_APP_ID/SECRET`。解析器两种都要认，否则报 `KeyError: 'FEISHU_APP_ID'`。

### 执行器与守护

- 守护：`daemon.sh`（background=true + persist_on_release，60s 检查进程，不在就拉起）。别再挂 hermes cron 做看门狗——会每 5 分钟往 DM 刷消息。
- 任务文件字段：`task_ref / platform(grok|muse) / prompt / schedule / chat_id / app`。`app` 决定用哪个机器人凭证发消息，与 platform 独立（可用 grok 机器人推 muse 结果）。
- watch 状态 `/opt/nas/volume2/2-AI/A2A/cloud-tasks/state/watches.json`；定时任务常驻 watch，每次新 run 成功都推一次。

## A2A 派任务给 grok

写 `inbox/task_<ref>_<ts>.json`：`{to:grok, from, task_ref, ts(+08:00), instruction, model?(默认grok-heavy), first_response_minutes?}`。worker 产出 `results/result_*.md` + `outbox/receipt_<ref>_grok_*.json`（PROGRESS→DONE），完成 move 到 processed/。
worker 是**顾问型**（只产文本），不能执行 shell、不能操作蜂群系统、不能在 xAI 云端跑代码（网页逆向无官方 computer-use API）。

### Grok 云端内部 REST API（实测可用，免费账号）

| 动作 | 接口 |
|---|---|
| 列表 | `GET /rest/automations` |
| 建任务 | `POST /rest/automations` body=`{content:{name,prompt,notificationMethod:"DEFAULT",modeId:"fast",icon:"l:zap:inherit",workspaceId:""},triggers:[],schedules:[{taskCadence,isEnabled,timezone,timeOfDay,dayOfYear}]}` |
| 立即跑 | `POST /rest/automations/{id}/run` |
| 查 run | `GET /rest/automations/{id}/runs` → `status: TASK_RESULT_SUCCESS` + `conversationId` |
| **取正文** | `GET /rest/app-chat/conversations/{cid}/responses` → `responses[].sender==ASSISTANT` 的 `message` |
| 删除 | `DELETE /rest/automations/{id}` |

坑：
- `schedules` 不能为空（报 `an automation needs a schedule, triggers, or both`）；`content` 必须包在 `content` 键里（否则 `content is required`）。
- 免费账号的 automation **排队约 4 分钟**才真跑，别把 300s 当超时判死；用 watch 模型异步盯。
- 正文含 `<grok:render card_id=...>` 内部标签，必须正则清掉再发飞书。
- run 对象本身**不含答案**，只有 conversationId，正文在 app-chat 接口。
- 自动化会话不在 `app-chat/conversations` 列表里（那是普通聊天），只能按 cid 直取 responses。

### Muse

muse 的 Goals 是**对话式**创建（“先一起在聊天里细化目标”），UI 是重度 SPA、`/api/falco` 只是遥测，硬啃 UI 不划算。走 muse2api `/v1/chat/completions`（Muse Spark 在云端跑），key 在 `/opt/data/services/muse2api/api_key`(600)。muse 任务的 schedule 目前不生效（muse2api 是同步接口）。

🔴 **muse 首字超时硬编码坑**（engine.py）：`first_token_deadline = t_sent + 40.0`，而 muse 正常首字就要 30-60 秒（VM 冷启动更久），所以会间歇性报「等待助手首字响应超时」。已改成 120.0；同时把 `if time.time() - t_sent > 14.0` 的「Still sending / Connecting...」判死改到 60.0（冷启动时这两个提示是正常的，不是故障）。改完必须 `docker cp` 进容器 + `docker restart`，因为 compose 只挂 `./data`，源码在镜像里；宿主 `/home/DY/muse2api/engine.py` 也要同步改，否则下次 build 回退。

排查 muse 失败时先看两处：`docker logs muse2api | grep 保活`（账号会话是否续上，ok=False 或 SSLError = 网络/代理）、桥日志的 `CHAT_FAIL/CHAT_ERR`（带耗时和上游原文）。

**别拿用户截图判断这条链坏没坏。** 蜂群里可能同时存在两个显示名都叫「muse 机器人」的东西（我们的 muse2api 桥 / muse 沙箱里 BOSS 自装的 Hermes 小林），但**别急着下「这是另一只 bot」的结论**——这恰恰是最容易错的一步，用户会立刻纠正你。判据是日志里的原话：`docker logs muse-feishu-bridge | grep "<用户那句原话>"`，看到 `RECV ... "原话"` 紧跟 `CHAT_DONE <ms> <字数>` 就说明**这条链已经答了**，问题在上游答的内容，不在传输。

### 🔴 云端 agent 的「自我认知」坑（答非所问的真根因）

muse-spark 跑在一台**持久化 Linux VM** 里，那台 VM 同时装着 BOSS 的 Hermes（小林）。用户问「你修好了吗」，它就去跑 `hermes gateway status`，把**沙箱里小林的故障当成自己的状态**回报（「Gateway is not running、PID 消失、uptime 1 小时」）。桥是通的、上游也答了，只是答的是别人的事。

**排查顺序（先证上游，再怀疑桥）：**
1. 桥日志找 `RECV` / `CHAT_DONE`——有记录＝消息进了链路且已回复，别在传输层找 bug。
2. **把用户那句原话原样打给上游**：`curl -s -X POST <上游>/v1/chat/completions -H "Authorization: Bearer $(cat api_key)" -d '{"model":"muse-spark","messages":[{"role":"user","content":"<用户原话>"}]}'`。如果上游单独跑也答「gateway 没运行」，根因就定了：是 agent 的上下文理解，不是桥。
3. 复现成功后加 system 约束再打一次，确认回复变成「就这个对话里的我来说……」，再固化进代码。

**修法：给桥注入身份 system prompt。** muse2api 支持 `system` role（实测有效）。桥里用环境变量可覆盖的常量，别写死：

```js
const SYS_PROMPT = process.env.MUSE_SYS_PROMPT || '你通过飞书机器人与用户对话。用户说的「你」指的是这个对话里的你本人，不要理解成沙箱里运行的其他 agent 或服务。直接回答用户的问题，不要主动去检查系统服务状态。';
// 请求体：messages: [{role:'system',content:SYS_PROMPT},{role:'user',content}]
```

A2A worker 那条路径已有自己的 system prompt（蜂群 worker 人格），**别覆盖它**——桥里有两处 `chat/completions` 调用，只改对话那条。

**推论（适用于任何「云 agent + IM 桥」）：** 只要上游 agent 有自己的持久沙箱，它就会把沙箱里的进程/服务/文件当「自己」。凡是「你修好了吗 / 你还在吗 / 你的服务正常吗」这类自指问题，都会被理解成沙箱巡检。桥这层要显式划清「你＝这个对话」的边界，否则每次自指提问都答成别人的故障。

### 踩坑
- `__Host-` 前缀 cookie（muse 的 `__Host-hatch_one_tap`）不能用 Playwright `add_cookies`（domain/url 二选一都报错），要用 page 级 CDP `ctx.new_cdp_session(pg).send("Network.setCookie", {url:"https://muse.ai/",...})`。
- 飞书 `im/v1/messages` 发 400 多半是 chat_id 不属于该 app——open_id/chat 是应用维度，只能用该 bot 真正收到过消息的 chat_id。
- 凭证键名不统一：grok 的 `feishu_app.env` 是 `FEISHU_GROK_APP_ID`，muse 是 `FEISHU_APP_ID`，读的时候两种都要兼容。
- Playwright 的 `Response` 对象**没有 `resource_type`**（`AttributeError` 会打断整个事件监听器，表现为脚本卡死/超时而不是报错退出）。抓包过滤要用 `r.request.resource_type`。
- 抓 muse 内部接口时注意 `/api/falco` 只是遥测（`{"success":true,"accepted":N}`），不是业务接口；只过滤 `/api/` 会漏掉真正的 Next.js RSC/SSR 请求，过滤条件用 `resource_type in ('xhr','fetch')` 全量抓再筛。

## 新增一个机器人（通用配方）

同一套桥可以给任意「网页版模型 → OpenAI 兼容」上游复制一份。muse 机器人是第二例：飞书 app `cli_aa6a5bfc0cb8dd00`、宿主 `/home/DY/muse-feishu/`、上游 muse2api `:18610`、A2A 别名 `muse2api`。顺序固定：建应用 → 取 secret → 起桥 → 测发送 → 测接收 → 登记 A2A。

🔴 **接一个新平台前先确认它有没有官方 API——有就别逆向网页。** 逆向（grok2api/muse2api 那套）是拿不到官方接口时的兜底，维护成本全在「页面/接口一改就废」。已核实的对照：

| 平台 | 有无官方 API | 结论 |
|---|---|---|
| Grok 网页版 | 无（免费号） | 只能逆向；免费额度按档位分，见上表 |
| Muse | 无 | 逆向 muse2api `/v1/chat/completions` |
| Manus | **有**：`https://api.manus.ai` v2，`x-manus-api-key` 或 OAuth，含 task/project/file/**webhook** | 优先接官方，webhook 天然适配「派单→完成→推回」 |
| Cue（cue.im，Manus 2.0 的独立 app） | **无**，只有手机/桌面 App | 接不进飞书；它的「独立电话/邮箱/钱包/云电脑」能力也没在 Manus API 里暴露 |

别把 Cue 和澳洲的 Cue AI（cueai.app，规划器 App）搞混——两个产品同名不同家。

**1. 建应用走「一键创建智能体应用」**：`https://open.feishu.cn/page/launcher?from=backend_oneclick`，只填名称 + 头像，提交即自动预置机器人能力、长连接订阅、权限，并直接发布 1.0.0。
- 别用「创建企业自建应用」对话框：强制 240px+ 图标，上传后弹裁剪编辑器，点「创建」静默不提交（URL 停在列表页，没有任何报错），还要自己逐项补能力+权限+发布。
- 判据：提交后 URL 变 `/app/cli_xxx` 且页面出现「创建成功 / App ID」。

**2. 取 App Secret 靠点眼睛，不靠抓包**：`/app/<id>/baseinfo` 有多个 `.secret-code` 块，**block[0] 是 App ID，block[1] 才是 App Secret**。取 block[0] 会把 App ID 当 secret 存下来，长度看着也合理、不报错。块内 `span.secret-code__btn` 中 `svg[data-icon="VisibleOutlined"]` 是揭示按钮，点完读 `.secret-code__code` 的 `inner_text()` 得明文。Network 监听拿不到——接口返回的就是掩码。
- 验证：`tenant_access_token/internal` 返 `code:0`；再 `bot/v3/info` 看 `activate_status:2` 与 `app_name`。

**3. 发测试消息必须用 union_id**：用别处拿到的 open_id 发会报 `99992361 open_id cross app`——open_id 是应用维度的，同一个人在每个 app 下都不同。改 `receive_id_type=union_id` + `on_...` 才能跨 app 发到本人。

**4. A2A 别名先查冲突再占**：`grep -l '"to": "<别名>"' /volume2/2-AI/A2A/inbox/*.json`。已有发给别人的同名任务就换名（muse 机器人用 `muse2api`，因为 `to=muse` 的旧任务是 muse 沙箱里小林的 relay 线）。抢别名等于抢别人的活。

**5. 桥的部署与验收**：本地写 `server.js/.env/Dockerfile/docker-compose.yml` → paramiko SFTP 传宿主 → `sudo -n docker compose build && up -d` → 日志出现 `client ready` / `ws client ready`。`.env` 用本地 600 凭证文件拼好再传，传完 `chmod 600`，全程不回显。

## 部署踩过的坑
- SFTP 根映射：SFTP `/home/...` = 系统 `/home/DY/...`，写 `/home/DY` 报 No such file。
- 绿联 Docker UI 无 hermes 项目（命令行 compose 起的），加端口只能 SSH 改 yaml。
- write_file 不能写 /opt/nas（SAFE_ROOT=/opt/data），改 NAS 文件走 python/SSH 或先写本地再 cp。
- 飞书开放平台自动化用 Playwright over CDP（直连 CDP 报 403 origin）；BOSS Windows Chrome 9223 只绑 127.0.0.1 需 SSH 隧道；后台开标签不抢焦点。
- worker.js 时间戳用北京时手动格式化（容器 UTC）；结果 md 直接 writeFileSync，别 JSON.stringify（会落成字面 \n）。
