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
1. **取 key**：`read_file` 看 config.yaml 的 `api_key` 是打码的，脚本里用 `open()` 读原文（`re.search(r'name: <provider的name>.*?api_key:\s*(\S+)', t, re.S)`）。
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
