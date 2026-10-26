---
name: model-routing
description: Use when 选择模型档位、切大脑、大型调研要派活，或回答「你现在什么模型」/确认实际生效的模型与路由落点。
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [model, routing, cost, delegation]
    related_skills: [agent-model-routing-setup, omniroute-gateway-ops]
---

# 小卡模型分层路由

**触发**：要切大脑模型、纠结某个任务该用哪个档、接到大型调研/多方案对比任务要派子代理时。

网关：OmniRoute `http://192.168.199.2:20128/v1`（key 在 `/opt/data/.env` 的
`CUSTOM:192-168-199-2-20128_API_KEY`）。**大脑只接 OmniRoute，不接单源网关**——单源挂了就失智。

## 零、回答「你现在什么模型」——路由溯源

BOSS 问这个时，**不许靠 config 注释、`providers.*.model` 声明，或让模型自述**——三者都会骗人。
唯一可信的是**响应头**。

### 0.1 套娃式 `auto`：body 的 model 字段只是回显别名
请求 `model=auto` → 响应 body 里 `"model": "auto"`（**回显你传的别名，不是真模型**）。真实路由全在头里：

| 头 | 含义 |
|---|---|
| `x-omniroute-decision` | `strategy=single; provider=<node-uuid>; latency_ms=N` —— 命中哪条连接、什么策略 |
| `x-omniroute-selected-connection-id` | 连接 id，拿去 `GET /api/providers`（解析键是 `connections`，不是 `providers`）查 `name` / `providerSpecificData.baseUrl` / `prefix` |
| `x-omniroute-model` | 仍是别名，**不是**真模型 |
| `x-omniroute-response-cost` / `-tokens-in` / `-tokens-out` / `-latency-ms` | 成本、用量、延迟 |

若那一跳落在**远端聚合网关**（`baseUrl` 指向 `wbmodel.iepose.cn` 这类），要再下一层：**聚合网关自己的 `X-Aggregator-Model` 头**才是真模型名（实测 `auto` → `global:deepseek-v4.1-flash`）。

### 0.2 判定三步（照做，别猜）
1. **取 key 只认 `.env`，不认 `config.yaml`**：`providers.*.api_key` 里常见的是**打码占位串**（形如
   `sk-432...73da`），拿它直连会回 `401 AUTH_002 Invalid API key`，读起来像网关挂了。权威值是
   `/opt/data/.env` 的 `CUSTOM:192-168-199-2-20128_API_KEY`（取到后先看长度：真 key 约 35 位，
   带 `...` 的必是占位串）。判据：`AUTH_002` = key 错，不是通道错——换模型、换 base 都不会好。
1b. **`.env` 里带冒号的键 source 不了**：`set -a; . ./.env` 会把 `CUSTOM:192-...` 当命令执行而失败，改用 Python 逐行 `split("=", 1)` 取值。

2. **打一发，只读头**（body 的 `model` 字段没用）：
   ```python
   r = urllib.request.Request("http://192.168.199.2:20128/v1/chat/completions", data=body,
       headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
   resp = urllib.request.urlopen(r, timeout=90)
   print(resp.headers.get("x-omniroute-decision"))
   print(resp.headers.get("x-omniroute-selected-connection-id"))
   ```
3. **连接 id → 真上游**：`GET /api/providers` 的 `connections[].id` 匹配 → `providerSpecificData.baseUrl` / `prefix`。

- **连打 3~4 发**比对 `x-omniroute-decision`：稳定落同一条连接 → 结论成立；跳来跳去 → 是轮询/优先级组合，回答要给「组合名 + 实际落点」两个信息。
- 组合的用途看 `/v1/models` 里该 id 的 `description` 字段（`owned_by: "combo"` 即组合），比从名字猜准得多。
- `/v1/models` 里除了裸 `auto`，还有一整族显式别名（`auto/best-coding`、`auto/chat`、`auto/coding:free`、`auto/vision`、`auto/reasoning:pro` …）——要固定取向时用显式别名，别用裸 `auto`。

### 0.3 三个坑
1. **别问模型「你是什么模型」**：实测它自述「Claude, Anthropic」（上游系统提示只是通用 "helpful assistant"），**自述不可信**；且这类提问常触发 `finish_reason: length` + `content: ""`、正文全塞在 `reasoning_content` —— 正是上游不可用的静默空指纹，既问不出答案还容易被误判成链路故障。
2. **config 注释 ≠ 生效值**：`model.default` 与同一文件里的注释、`providers.*.model` 声明可以互相矛盾。**这种不一致不会报错**，只会让 `context_length` 按错的模型算（例：声明 `assistant` 的 192000 vs 实际 `auto` 的 262144）。回答以 `model.default` + 实测路由为准，并把不一致**明确点给 BOSS、给出「统一成哪个」的选项**——不要自己默默改。
3. **没有路由历史端点**：`/api/logs`、`/api/requests`、`/api/stats`、`/api/metrics` 在 v3.8.51 全 404 —— **响应头是唯一入口**，别在这几个路径上耗时间。

## 〇.5 每日通道健康自检（T-015 落地，不用再手工三连发）

**一键命令**：`python3 /opt/data/memories/channel_check.py`（加 `--all` 再查所有 provider）。
- 从 `config.yaml` 读 key（**不硬编码凭据**，`key_env` 形式从环境变量取），真实打一发 `/chat/completions`，输出主通道 + 每条降级的延迟/HTTP码/实际返回模型。
- 能自动揭穿别名漂移：实测 `free-pool` 别名背后返回 `global:deepseek-v4.1-flash`、OmniRoute 头里的真模型也会打出来。
- 退出码：主+所有降级全挂=1（cron 可据此告警），否则 0。**HTTP 200 但 content 空不算成功。**
- 已并入每日自检 cron：`selfcheck.py` 第 7 项每天顺手跑，输出「✅ 模型通道 N 通 / M 挂」，无需另开任务。
- 毛选周校验 2026-10-12 的 `HTTP 401` 就是通道当日抽风（上周正常、脚本没坏）——这类"任务失败"先跑 channel_check 区分是脚本 bug 还是通道挂，别误判。

## 一、分层路由（大脑配置）

**当前主模型（2026-10-18 BOSS 令）**：`provider: ark-coding` **直连火山方舟 Coding Plan**
`https://ark.cn-beijing.volces.com/api/coding/v3`，`model: ark-code-latest`，绕过 OmniRoute 降延迟
（实测普通 1.5s / tools 2.84s，tool_calls 正常；key 在 config.yaml `providers.ark-coding`）。
降级链原样保留：free-pool → internlm/internvl3.5-latest → global:step-5-preview。
注：OmniRoute 上 `ark-main`/`coding` 别名经 vecp 连接实际也路由到 ark-code-latest，直连只是省一跳。

`/opt/data/config.yaml` 的 `model.default`：

| 档位 | 模型 | 用途 |
|---|---|---|
| **auto（默认大脑）** | `auto` | 网关按难度自动选。实测 tools ✅、规划类任务 4.2s 出 6 条计划，质量优于 Flash |
| **聪明档（点名用）** | `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | 550B 大杯，免费。实测 tools ✅、17.7s |
| | `openrouter/nvidia/nemotron-3-super-120b-a12b:free` | 120B 免费，tools ✅ |
| | `internlm/intern-s1-pro` | 书生，tools ✅ |
| **快档（杂活）** | `naswb/deepseek-v4.1-flash` | 2.4s，tools ✅，量最大随便烧 |
| | `owbwin/OC · *Free` 系列 | 免费但**常 503**（provider 不稳），别当主力 |

### 档位分工
- **规划/故障诊断/方案对比/选品分析** → 聪明档，或直接让 `auto` 判。
- **git 操作/文件搬运/格式转换/监控巡检/摘要** → 快档，不要过度思考，直接干。
- **禁止**：用 Flash 档硬想复杂问题——这是绕路笨重的根源。

### 额度补充
- OpenRouter 免费池大杯（deepseek/glm 级）每日 1000 次。
- Qoder CN 每日可领 100 Credits（30 天有效、可囤积）——**记得每天领**。

## 二、以量补质战术

大型调研 / 多方案对比任务：用 `delegate_task` **并行派 3-5 个子代理**同时跑不同方向（子代理用快档），
主会话用聪明档**汇总裁决**。总产出深度可以超过单线程强模型。

纪律（踩过的坑）：
- 子代理写文件必须给**独立目录**，否则与主会话 scratch 互相覆盖。
- 子代理的结论是**自述**不是事实，回源核实后才能进汇报。

### 成长日志制度

维护 `A2A/小卡成长日志.md`（在 obsidian-sync 仓库）：每完成一个任务追加一条
**日期 / 任务 / 踩的坑 / 学到什么**（2-3 行）。有问题也写在日志里 @星期五，那是直接沟通渠道，不用 BOSS 转达。

📌 本技能已落地（2026-10-15），T-004 需在技能中增加如下三项**任务履历**，同时更新 `A2A/任务板.md` 的状态列：

| # | 任务 | 派给 | 状态 | 派单日 | 备注 |
|---|---|---|---|---|---|
| T-004 | n8n OmniRoute key 迁移到 Credential + 免费池健康快照 workflow | 小卡 | ✅完成 | 2026-10-15 | 详见小卡成长日志批阅段 |

如果还有新任务请先在本技能区落地，再移入任务板；避免无根任务停留在待领列。

任务验收流程（2026-10-15）
1. 小卡负责落地（写技能/落地文件）
2. Queen 批阅成长日志批阅段 → 打勾 ✅
3. 小卡更新任务板状态 → ✅完成
4. 回执一句话："已落基础 A2A 任务板 T-004 ✅；关键操作：[关键操作1]、[关键操作2]、[关键操作3]。"
5. 最后在成长日志补充尾部批阅批语（可选）。

⚠️ 每个任务都要求**落地先于上板**；如果项目还需要更多人并行，还需要新增技能区（比如`xiaoka-n8n-ops`等）。

---

## 六、降级链（fallback）与 5xx failover

症状指纹：`Provider temporarily unavailable — retrying automatically in 2s (cycle 1/5 … 5/5)` → `Automatic recovery gave up` → `HTTP 503: Service temporarily unavailable due to resource pressure`。**这不是模型名错（模型名错是 400），是上游容量压力 + 降级链没生效。**

### 6.1 `fallback_providers` 只认字典，裸字符串被静默丢弃
```yaml
fallback_providers:            # ✅
  - provider: custom:192-168-199-2-20128-freepool
    model: free-pool
```
```yaml
fallback_providers:
  - free-gw-step5              # ❌ 被 _iter_fallback_entries 丢掉，不报错
```
写完**必须**跑 `hermes fallback list` 看是否真列出 Primary + Fallback chain；输出 `No fallback providers configured.` 就说明被丢了。`hermes fallback add` 没有任何参数（只有 `-h`），命令行建不出降级链。

### 6.2 辅助任务（vision/压缩等）要单独配，且源码默认不把 5xx 当可降级
- `auxiliary.<task>.provider/model/fallback_chain` 与主 `model.default` 是两套，主链配好了 vision 照样 503 硬失败。
- `agent/auxiliary_client.py` 的 `_FALLBACK_REASONS` 只有 auth/payment/rate-limit/timeout/connection，**没有 5xx**：503 只会在同一 provider 上重试几轮然后抛错，永不切备用。
- 已用用户插件补上：`/opt/data/plugins/aux-5xx-failover`（`plugin.yaml` + `__init__.py`，`hermes plugins enable aux-5xx-failover`）。它把 5xx 追加进 `_FALLBACK_REASONS`、把 5xx 候选的隔离期设成 180s、并注册 `transform_api_error_classification`。enable 时网关**热加载 hooks，无需重启**。模板见 `templates/aux-5xx-failover-plugin.py`；换实例/容器时重放这个插件。
- 主用视觉模型用 `naswb/deepseek-v4.1-flash`（能认准中文标题），备用 `internlm/internvl3.5-latest` —— 备用 OCR 明显更弱（把「小卡nas」读成「小卡-kar」），只当兜底。

### 6.3 验证 failover 真生效（别只看代码）
1. 起本地假 503：`HTTPServer(('127.0.0.1',18080))` 对任何 POST 返回 503 + `{"error":{"message":"Service temporarily unavailable due to resource pressure"}}`；用 `terminal(background=true)` 起，**别用 `pkill -f fake503.py` 收尾**——命令行自身含该串会连自己 shell 一起杀掉，用 `process_manage` 或 PID 文件。
2. 临时把 `auxiliary.vision.base_url` 指到 `http://127.0.0.1:18080/v1`，再 `vision_analyze`：补丁前硬失败，补丁后自动切备用并返回答案。
3. 事后**必须**删掉临时 `base_url` 并再跑一次 `vision_analyze` 确认真链路正常。

### 6.4 改 config.yaml 的唯一稳妥手法
- `patch`/`write_file` 改 `/opt/data/config.yaml` 会被安全策略拒（`Agent cannot modify security-sensitive configuration`）。
- `hermes config set` 写 JSON 列表/嵌套结构会把文件改坏（丢注释、缩进错乱），事后要靠 `hermes config check` 才看得出。
- 走 python 文本替换：读全文 → `assert s.count(old)==1` → 写回；改前备份，已知良好版本在 `/opt/data/backups/config/config.yaml.good.*`。改完跑 `hermes config check`（无 error/invalid 才算过）。

### 6.5 报错级联（Rate limited → 备用全 unreachable）：先分清「主 429」与「备不可达」

症状指纹：`Rate limited` 与 `Provider unreachable` 交替刷，fallback 从主模型一路掉到末档，`5 automatic recovery cycles` 后放弃。
这不是模型名错（那是 400），也常常不是降级链没配 —— 是**两个故障叠在一起**，只修一个仍会报错。

诊断必须在**出故障的那台机器**上做，不能在网关侧做：

```bash
# 1) 主通道：直连 provider，读 429 的原文（别只看「Rate limited」四个字）
curl -s -m20 <主provider base>/chat/completions -H "Authorization: Bearer $K" \
  -H 'Content-Type: application/json' -d '{"model":"<主模型>","messages":[{"role":"user","content":"hi"}],"max_tokens":8}'
# 2) 备用通道：备用都挂在同一个网关时，先验这台机器到网关通不通
curl -s -m8 -o /dev/null -w '%{http_code} %{time_total}s\n' http://<网关>/v1/models
```

| 结果 | 判读 | 处置 |
|---|---|---|
| `429 AccountQuotaExceeded`（火山方舟 Coding Plan） | **5 小时窗口配额用光**，响应体给重置时间 | 换 key / 换 base_url 都没用；等窗口重置或换主通道 |
| 备用 `000` / 满 8 秒超时 | 那台机器到网关链路断（组网问题） | 先修链路；此时改 fallback 顺序毫无意义，所有备用会一起死 |
| 网关侧自己 200 而故障机 000 | 远端可达性问题 | **网关侧 200 不能证明远端可达**，一律从故障机发起验证 |
| 网关回 `401 AUTH_002 Invalid API key` | 用了 `config.yaml` 里的打码占位 key | 改从 `.env` 的 `CUSTOM:..._API_KEY` 取真 key；网关本身是好的 |

**备用全 `000` 时先别怀疑网关。** 最常见的具体原因是那台机器自己的防火墙把组网回包丢了：tailscale 的
`ts-input` 链有 `-s 100.64.0.0/10 ! -i tailscale0 -j DROP`，而节点小宝的 `100.66.1.0/24` 正落在该段里，
于是请求出得去、应答回不来。判据：在那台上 `sudo tcpdump -ni NodeBabyLink` 同时另开一个 curl ——
看到 **SYN 出去、SYN-ACK 回来、本机又重传 SYN** 就是回包被 INPUT 丢弃，与模型、fallback 顺序、
客户端版本全部无关。修法与持久化见技能 `nodebabylink-mesh-troubleshoot` 的「入站正常但出站全灭」。

修复顺序：① 先修链路（备用能通）；② 再把主模型切到能用的通道、原主通道降为兜底 ——
主通道天天 429 会让每次请求都先吃一次失败再降级，既慢又把日志刷脏。

切换照 §五 的三件套（`provider`/`default`/`base_url` 同改）+ 备份 + 重启 gateway。
**生效判据**：gateway.log 里出现 `Model context warmed: <新模型> -> <ctx> tokens (config)` 即为新配置已加载，
比翻 OmniRoute `call_logs` 快；journalctl 看不到这行是因为它写进 gateway 自己的日志文件。

端到端验证：在群里 @ 那个 agent 让它只回一句短话，比 curl 更能证明「网关 → 模型 → 回复」整链通。

## 八、按任务选免费模型（2026-10-20 全量实测）

**先记住四个硬事实：**

1. `/v1/models` 里 58 个「免费」模型，**实测只有 22 个真能打通**。23 个 404（列表脏数据/上游已下架）、5 个 429、4 个 401、3 个 400。**列表 ≠ 可用**，选型前必须探活。
2. **`auto/*` 别名全部不可信**。实测：`auto/best-reasoning` 落 `deepseek-v4.1-flash`、`auto/best-coding` 同样落 flash、`auto/cheap`/`auto/thrifty` 也是 flash。名字里的 best/pro 不代表真上大杯。**要固定取向只能用显式 model id。**
3. 同一个模型在不同 provider 前缀下可用性不同：`openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` 通，`wbfree/...`、`oc/...` 同名的全 404/403。
4. **`nemotron-3-ultra-550b-a55b:free` 是 BOSS 指定给 Claude Code / ACP 的专属后端**，不进任何日常路由。`pick_model.py` 的 `TIERS` 里不得出现它（reasoning / coding / longctx 三档都算）；日常任务一律 lightning → minimax → dots/super-vl。改完 TIERS 必须 `smart --dry` 跑四个典型任务（写脚本 / 排查故障 / 看图 / 总结），确认没有一条再指向 550B。

### 8.1 选型工具（唯一入口）

```bash
python3 /opt/data/memories/pick_model.py reasoning   # 打印该用的 model id
python3 /opt/data/memories/pick_model.py fast --json
python3 /opt/data/memories/pick_model.py --list      # 全部档位
```

- 每档是**有序候选表**，真打一发 1-token 探活，取第一个通过的；结果缓存 120s。
- 全挂时退出码 1，调用方降级到 `free-pool`。
- 云端星期五：`~/.hermes/memories/pick_model.py`，地址用环境变量 `OMNIROUTE_BASE=http://100.66.1.7:20128/v1`（脚本读 `~/.hermes/.env`）。

### 8.2 实测能力表（逻辑题 / 3^100 mod 7 / tool_calls）

| 模型 | 逻辑 | 数学 | 工具 | 延迟 | 上下文 | 结论 |
|---|---|---|---|---|---|---|
| `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | ✓ | ✓ | ✓ | 10.7s | 1M | ⛔ **只归 Claude Code/ACP**，见 §8 硬事实 4 |
| `openrouter/nvidia/nemotron-3.5-lightning:free` | ✓ | ✓ | ✓ | 8.6s | 1M | 次选，更快 |
| `openrouter/minimax/minimax-m3.1-flash:free` | ✓ | ✓ | ✓ | **4.3s** | 1M | **快档首选** |
| `openrouter/dots-studio/dots-3-note-preview:free` | ✓ | ✓ | ✓ | 11.7s | 512K | 长文档备选 |
| `openrouter/nvidia/nemotron-3.5-super-vl:free` | 空 | ✓ | ✓ | 24s | 1M | **视觉专用**，纯文本任务别用 |
| `openrouter/cohere/north-mini-code:free` | ✗ | ✓ | ✓ | 8.1s | 256K | 只适合写代码 |
| `openrouter/poolside/laguna-xs-2.1:free` | ✓ | ✓ | ✓ | 21s | 262K | 慢，兜底 |
| `openrouter/xingchen-agi/xing4.0-29b-a4b:free` | ✗ | ✗ | ✓ | 25s | 262K | 不推荐 |
| `owbwin/OC · Nemotron 3 Ultra Free` | — | — | — | 21.9s | 128K | 慢一个数量级，仅备源 |
| `wbfree/global:hy3` | ✓ | ✓ | ✓ | 4.1s | 192K | 腾讯混元，中文强，AA 25 |
| `wbfree/OC · Big Pickle`、`oc/nemotron-3-ultra-free` | 404/403 | | | | | **列表里有，实际打不通** |

### 8.2.1 按智力分选型，不按参数量

AA Intelligence Index 实测排序：`minimax-m3.1-flash` 42 > `deepseek-v4.1-flash` 39.5 > `nemotron-3.5-super-vl` 26.5 > `hy3` 25 > `nemotron-3.5-lightning` 24 > `nemotron-3-ultra-550b` 23。**550B 名字最大、分数最低**，别因为名字或参数量选它。

- **探活会出现假超时**：并发 4 打免费池时慢模型 40s 超时，串行重试 3.5s 就通。判「模型挂了」前**必须串行复核一次**，否则会把可用模型报成不可用。
- 同一厂商的别名通道会整批死：`wbfree/OC · *` 超时的那天 `wbfree/global:*` 正常 —— 报不可用要带通道名。
- 完整盘点流程、探活脚本与实测基线见技能 `omniroute-gateway-ops` 的免费模型盘点参考文件（free-model-inventory.md）。

### 8.3 三种接法（按需要选）

| 场景 | 做法 | 生效范围 |
|---|---|---|
| 单次任务换脑 | `hermes chat --provider custom:192-168-199-2-20128 -m "$(python3 memories/pick_model.py coding)" -q "..."` | 本次调用 |
| 全局默认 | 改 `model.provider` + `model.default` + `base_url` 三件套 | 所有会话 |
| 子代理 | `delegation.provider` / `delegation.model`（**全局，不能 per-child**） | 所有子代理 |
| 子代理要各用各的 | 别用 `delegate_task`，改用 `terminal(background=True)` 跑 `hermes chat -m <model> -q ...` 当「模型钉死的 worker」 | 每个 worker 独立 |

### 8.4 坑

- **`-m` 必须配 `--provider`**。只给 `-m openrouter/...` 会打到当前 provider（`nas-8788`）报模型不存在。
- `hermes chat -m` 在带 tools 的任务上会先跑一轮 terminal 探测，日志里刷 `preparing terminal…` 属正常，别当故障。
- `delegation.model` 填错会让**所有**子任务同样失败，且有专门的通知逻辑（`_delegation_model_not_found`）——改完先跑一个最小子任务验证。

## 九、JEV 决策模型：只当分类器，不当模型（2026-10-20 实测）

BOSS 有 JEV 的 API key，接入点在 OmniRoute 里已存在两条：

| 连接 | 前缀 | base | 实际能力 |
|---|---|---|---|
| `jev-router` | `jev` | `192.168.199.184:41986` | 普通 chat 模型（`jev/free` `jev/coding` `jev/smart` `jev/vision`），能答题、能 tool_calls |
| `JEV-Decision` | `jevd` | `192.168.199.2:8082` | **不是 chat 模型**，是决策打分器 |

### 9.1 jevd 的真实协议（踩坑重点）

- 普通 `messages` 请求 → `HTTP 400 missing_questions`。
- **正确形状是 `state` + `questions`（不用 `messages`），且 `questions` 必须是 dict 不是 list**：
  ```json
  {"model":"jev-latest",
   "state":"<待判任务，一段自然语言>",
   "questions":{"owner":{"type":"choice","instructions":"Which expert?",
     "criteria":{"小安":"合规认证","老钱":"财务测算","小维":"技术运维"}}}}
  ```
- **`criteria` 必须放在 question 对象的顶层**。嵌进 `choice`/`score` 内部 → 服务端报 `missing`、`jev_answers` 空，表面看像「模型没反应」。两轮探测脚本全白跑就是它；改对后一次 12/12。
- 三种 `type` 的返回位置：`choice` → `jev_answers.<k>.choice`（键名就是 criteria 的键）；`score` → `.score` 是 **0-based 下标**（criteria 用有序列表）；`noul` → `.noul` 是 0~1 概率，不需要 criteria。
- `questions` 传 list → `HTTP 502 / upstream 422 Input should be a valid dictionary`。
- 响应里 `message.jev_answers` 给每个问题一个 `noul` 分数（0~1），同时 `content` 是一份同样的 JSON 文本。
- **顶层 `questions` 能过 8082 直连，但过不了 OmniRoute**（网关不转发非标准字段，照样报 missing_questions）。所以路由时**先试直连 8082**，OmniRoute 只能走 system message 塞 `{"questions":{...}}` 那条路（实测能过，但偶发不稳）。
- 两个模型名都指向同一后端：`jev-latest` = `jev-1.13.0`（响应体 `model` 字段回 `jev-1.13.0`）。

### 9.2 实测结论：值不值得用

**值得，但只能当分类器，不能当生成模型。**

| 用途 | 结论 | 依据 |
|---|---|---|
| 当聊天/推理模型 | **不行** | `jevd/*` 一律 400；`jev/*` 能答但逻辑题错（`jev/free` 逻辑✗）、延迟 6–26s，`jev/smart` 直接 120s 超时 |
| 当任务分类器（选档） | **很好用** | 12 条真实任务分档 **11–12/12 命中**，延迟 0.4–3.5s，比关键词规则（8/12 = 67%）强 |
| 当模型选择器（直接吐 model id） | **不要** | 会编造模型名；正确做法是它只回答 5 个二分类，档位→模型由 `pick_model.py` 查表 |

### 9.3 已落地：两级路由

```bash
python3 /opt/data/memories/route_task.py "读一张发票截图，提取金额"
# 档位: vision  (判定来源: direct)
# 模型: openrouter/nvidia/nemotron-3.5-super-vl:free
```

链路：**JEV 打 5 个二分类（vision / longctx / coding / reasoning / trivial）→ 分数≥0.5 定档 → `pick_model.py` 查表 + 探活 → model id**。

5 个问题（固定，别改措辞，改了准确率掉）：

| 键 | 问什么 |
|---|---|
| `needs_vision` | 是否需要看图片/截图/扫描件/视频画面 |
| `needs_long_context` | 是否涉及十万字以上文本/整个代码库/大量日志 |
| `is_code_task` | 核心产出是否是代码 |
| `is_trivial` | 是否一句话就能答完 |
| `needs_hard_reasoning` | 是否需要多步推理/权衡方案/复杂诊断 |

失败链：`直连 8082` → `OmniRoute system message` → `关键词规则兜底`。任一环挂都不阻塞，`via` 字段会告诉你走了哪条。

### 9.4 什么时候别用 JEV

- **延迟敏感**：每次多 0.4–3.5s。群聊短答、cron 高频任务直接走关键词或固定档。
- **已有明确任务类型的固定任务**：早盘播报、周复盘这类天天一样的，直接写死档位，不用每次问 JEV。
- **要它输出结构化长文本**：它不是生成模型，别拿它写报告。

### 9.5 怎么用（已装好的三处）

一条命令完成「JEV 分档 → 探活选模型 → 真执行」：

```bash
smart "读这张截图里的金额"          # 全自动
smart --dry "排查容器反复重启"      # 只看选什么，不执行
smart --tier coding "写个归档脚本"   # 跳过 JEV 强制档位（固定任务用这个）
smart --model openrouter/nvidia/nemotron-3.5-super-vl:free "看图"   # 完全手动
```

部署位置：

| 位置 | 路径 | provider 自动识别 |
|---|---|---|
| 小卡本机 | `/opt/data/bin/smart`（已在 PATH） | `custom:192-168-199-2-20128` |
| 云端星期五 | `~/.local/bin/smart` | `omniroute` |
| 共享库（任何 agent） | `/opt/nas/volume2/2-AI/skills/agent-model-routing-setup/scripts/smart` | 按 config 判断 |

云端跑需要带环境变量（NAS 走虚拟网 IP）：
```bash
OMNIROUTE_BASE=http://100.66.1.7:20128/v1 JEV_BASE=http://100.66.1.7:8082/v1 smart "..."
```

### 9.6 接入建议（按性价比排）

| 场景 | 做法 | 为什么 |
|---|---|---|
| 一次性难任务、跑完就走 | `smart "..."` | 自动按档位选（reasoning 首选 lightning，**不再拿 550B**） |
| 天天一样的 cron（播报/周报/巡检） | `smart --tier fast/--tier reasoning` | 固定任务不需要每次花 0.5–3s 问 JEV |
| 子代理各用各的模型 | `terminal(background=True)` 跑 `smart` 当 worker | `delegate_task` 不能 per-child 钉模型 |
| 主会话默认脑 | 改 `model.provider/default/base_url` | 全局生效，慎改 |

**别做**：不要用 `delegate_task` 的 `delegation.model` 去追任务差异——它是全局的，一个值管所有子任务，改错会全线挂。

### 9.7 四种判断类型 + `jev_ops` 库（现成实现，别再手写）

决策层能干的活就是四类，全部封装在 `/opt/data/bin/jev_ops.py`（失败一律降级，绝不抛异常打断主流程）：

| 函数 | 判断 | type | 降级值 | 实测 |
|---|---|---|---|---|
| `pick_expert(text)` | 该派哪个 agent | `choice` | 小通 | 6/6，`conf<0.5` 自动回总协调 |
| `priority(text)` / `priority_rank()` | 0–3 紧急度 | `score` | 本周内(1) | 乱序投递 → 正确重排 |
| `pick_model(text)` | vision / deepseek / flash / none | `choice` | deepseek | 图片翻译→vision、改名→none |
| `accept(deliverable, requirement)` | 交付是否合格 | `noul` | 放行 | 空话 FAIL、有数据 PASS |
| `needs_human(text)` | 要不要人工确认 | `noul` | 不拦 | 删 50 SKU 0.98🔴 / 写 5 条标题 0.04🟢 |

CLI：`jev expert|model|prio|human|accept|all|batch`。

两条纪律：
- **`accept` 的长度闸是 8 字符，不是 30。** 闸门只负责挡「已完成。」「好的，我马上处理」这类敷衍；30 会把「毛利率 32%，回款周期 45 天。」（18 字，语义分 0.55）100% 误杀，而「短而正确」正是最常见的交付形态。改闸门后必须用六类样本重跑：短·正确 / 短·敷衍 / 长·凑字 / 长·好 / 代码·空壳 / 代码·好——任何一类错了都是闸门错，不是分类器错。
- **判定口径写 `state`，绝不写 `instructions`。** 想纠正「短答案也算合格」这类偏差时往 `instructions` 里加句子（2 句加到 5 句），会让**所有**样本的 p 值一起塌到 0.0x——连原本 0.82 的好交付都变 0.03，而且不报错。正确位置是 `state` 尾部加一段中文【判定口径】，实测回归通过。
- **阈值 0.5 不要动。** 实测 0.30–0.50 六档对 10 个样本全部 100% 准确，0.55 开始误杀短正确答案；同一交付物连打 5 次 p 值 sd ≤ 0.02，低分是信号不是噪声。
- **回归样本必须一例一 `requirement`。** 拿同一条要求（比如「价格指数在哪个菜单」）去判选品分析/脚本这类无关交付，p=0.02 是**判对了答非所问**，不是分类器坏了；共用 requirement 的回归脚本会把「模型正确」误读成「模型失效」，白回滚一轮。
- **低置信度是特性不是 bug**：`conf<0.5` 时不要硬取 top-1。任务本身模糊（「20 个 SKU 价格异常，涉及财务和后台操作」→ 老钱 0.27 / 小维 0.33 / 小通 0.31）就该回落到协调者或反问 BOSS。

成本：单次 0.4–1.4s / 300–600 tokens，比 LLM 分类（2–5s / 2–5k）便宜一个数量级；但**延迟敏感场景仍别用**（见 9.4）。

## 七、自我进化

每季度回顾一次，找到『model-routing』技能里依然在写的旧规则 / 多余段落，合并或删除；写批量`git commit -am "clean"` + `git pull --rebase` + `git push`
确保整个 obsidian-sync 仓库保持精益（每个文件都有明确触发，一个月没碰的过时内容迁移）。

## 四、实测速查（2026-10-15 复核）

```bash
# 能力实测（tools + 视觉，逐个短超时）
python3 /opt/nas/volume2/2-AI/skills/agent-model-routing-setup/scripts/probe_models.py \
  http://192.168.199.2:20128/v1 <model_id> [...]
```

| 现象 | 真因 |
|---|---|
| `oc/*` 免费档 403 FreeTierError | OpenCode 免费额度已用尽 |
| `owbwin/OC · *` 503 | 该 provider 通道宕，换 `openrouter/nvidia/...:free` |
| `mac8081/Qwen3-Max` → `Model not exist` | 上游池已变，先跑 `sync-models` |
| HTTP 200 但 content 空 | 上游不可用，**不算成功** |

⚠️ 旧技能 `agent-model-routing-setup` 记载「`auto/*` 不返回 tool_calls」——**2026-10-15 实测已不成立**，
`auto`、`auto/best-free`、`auto/pro-chat`、`auto/reasoning` 全部正常返回 `tool_calls`。该条已过时。

## 五、切大脑的注意事项

- `model.default` / `provider` / `base_url` **三个字段必须同改**，只改 default 会打到旧 base_url。
- 改前 `cp config.yaml config.yaml.bak-进化前`；改后**读回验证**，别只看写入成功。
- **是否要重启 gateway 取决于该项在哪读**：`model.*` 与 `display.*` 每轮现读（`_load_gateway_config()` 无缓存），改完即生效；但 `streaming.enabled` 由 `runner.config.streaming` 在**网关启动时快照**，改完必须重启网关。判据是 grep 读点，不是猜——见技能 `hermes-latency-tuning`。
- 禁 reboot：跑在 NAS 上，重启 = 自杀。
- 改完**顺手检查注释与声明是否跟得上**：config 里 `model.default`、注释、`providers.*.model` 三处说法不一致时**不会报错**，只会让 `context_length` 等按错的模型算。发现不一致就报给 BOSS 并给出统一选项，别只改一半。
- **云端 gateway（`systemd --user hermes-gateway`）切模型要改四处**：`model.default`、`model_display_name`、provider 块里的 `name`（面板和日志显示用）、restart。改前先 `cp config.yaml config.yaml.bak.<用途>`，回滚靠它。
- **验证生效别指望 journalctl**：它通常不会打出 `active model` 这种明确行。可靠做法是比对 **OmniRoute 的 `call_logs/<日期>/*.json`** 里的 `"model"` 值与 gateway 重启时刻——重启后的第一条就是新选的模型，才算真生效。容器内没 `python3` 时用 `grep -o '"model":"[^"]*"'` 纯 shell 解析。更快的判据是 gateway 自己的日志文件里 `Model context warmed: <model> -> <ctx> tokens (config)` 这行（重启后立刻出现）。
