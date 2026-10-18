---
name: hermes-latency-tuning
description: "Use when agent 响应慢、要提速、或要做改前改后延迟基准。四层拆解 + 基准纪律。"
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [performance, latency, benchmark, gateway, config]
    related_skills: [model-routing, omniroute-gateway-ops, xiaoka-execution-discipline]
---

# Hermes 响应速度诊断与调优

**触发**：BOSS 说「太慢 / 响应速度优化 / 秒表测一下 / 报两个数字」，或要给出改前改后延迟对比。

## 铁律：先拆解，再动手

没有分层数据之前不改任何配置。用户感知的「慢」里通常只有一小块是模型——直接换模型档位往往零收益。

## 一、四层拆解（按顺序量，每层一条命令）

| 层 | 怎么量 | 典型值 |
|---|---|---|
| 启动 | `for i in 1 2 3; do S=$(date +%s%N); hermes --version >/dev/null; E=$(date +%s%N); echo $(( (E-S)/1000000 ))ms; done` | 3.0-3.3s |
| 模型裸延迟 | 直接 POST 网关 `/v1/chat/completions`，小 prompt 与 ~100k token prompt 各 2-4 发 | 小 1.2-1.6s；114k tokens 2.7-4.0s |
| 工具往返 | 同一入口分别问「要工具」和「不要工具」的问题（`现在几点` vs `1+1等于几`），差值即工具成本 | ~3.5s |
| 上下文装配 | 总耗时减以上三项；`--usage-file` 看 `input_tokens` | 简单问答 69k tokens |

`--usage-file <path>` 是拿到 `input_tokens` / `cache_read_tokens` 的唯一入口，做基准时每次问答都带上。
可直接跑 `scripts/latency_probe.py` 一次性出前两层。

## 二、基准纪律（最容易报出假结论的地方）

**prompt cache 会让同一命令的耗时双峰分布。** 冷缓存首跑可能 28s，热缓存稳态 20s——同配置、同机器、同问题。

规则：
- 每组至少 3 发，**报中位数**，不报单次。
- 每发读 `cache_read_tokens`：为 0 就是冷跑，**剔除**。
- 两组区间不重叠才算真差异；重叠就是噪声，不许报「变快/变慢」。
- 改前改后必须同条件：同问题、同顺序、同缓存温度、同命令形式。

真实反例：冷缓存 3 发得 28.8/27.7/27.1s，据此报「改后慢了 5.7s」；补 3 发热缓存得 20.4/21.4/20.1s，结论翻转为「无差异」。**先看缓存，再看差值。**

## 三、配置开关：键路径 + 生效方式

| 想要的效果 | 键路径 | 生效方式 |
|---|---|---|
| 回复逐字显示（流式） | `streaming.enabled`（嵌套，不是顶层 `streaming`） | **需重启网关** |
| 收到消息立即回「收到,处理中」 | `display.busy_ack_detail` | 每轮现读，免重启 |
| 多行指令合并意图而非排队 | `display.busy_input_mode: steer` | 每轮现读，免重启 |
| 换大脑 / 上下文长度 | `model.default` / `model.context_length` | 免重启 |

- **`display.*` 不在 `gateway:` 段。** `gateway/display_config.py` 的 `resolve_display_setting` 读 `display.*`，写进 `gateway:` 段静默不生效。
- **`streaming.enabled` 只认启动快照**：`run_turn_runner` 里 `scfg = runner.config.streaming`，`StreamingConfig.enabled_for()` 用这个对象；而 `display.*` 走 `_load_gateway_config()`（每次现读、无缓存）。**判据是 grep 读点，不是猜。**
- 部分键 `hermes config set` 要加 `--force` 才落盘（`display.busy_ack_detail` 实测），写完必须回读确认。
- 平台覆盖只能收窄不能打开：`display.platforms.<plat>.streaming: false` 会压掉全局 `true`；没有 `display.platforms` 段才是跟随全局。

## 四、感知延迟 ≠ 墙钟时间

- `busy_ack` 与流式只改**首字可见时间（TTFB）**，不改总耗时。用 CLI 总时长去验证这两项，必然得出「没用」的错误结论。
- 验证流式要看网关路径，且平台适配器必须有 `edit_message`（飞书适配器有，可流式）。
- 反过来，往 system_prompt 里加「少走步骤」的自律条款，只在**步骤数真的 >1** 时才有收益。先数工具调用次数，再承诺提速；简单问答本来就 1 次调用，加条款等于零收益。
- 结论里必须分开写「总墙钟」和「首字可见」两个指标，别混成一个数。

## 五、真正的瓶颈通常是上下文装配

系统提示词里的技能清单是最大的一块：**450+ 个 SKILL.md 的描述 ≈ 34k tokens**，每个简单问答都要重过一遍链路。
方向：按类目只把高频技能放进 prompt，其余走按需检索（`find-skills` 类技能）。这是唯一能把 20s 压到 10s 量级的改动——砍模型档位没用，模型本身只占 1.5s。

## 六、在容器里重启网关（安全做法）

- 先查重启策略：`docker inspect <容器> --format '{{.HostConfig.RestartPolicy.Name}}'`。`unless-stopped` 才能安全重启；`no` 会一去不回。
- Hermes 官方镜像里网关是 `/init` 的 **main program**（`docker/main-wrapper.sh`），不是 s6 监督服务——**杀掉进程 = 容器退出**，不会自动拉起。重启一律用 `docker restart`。
- 当前回合正由这个网关投递，**立刻重启会把回执弄丢**。先放延迟重启：`ssh <host> 'sleep 120; sudo -n docker restart <容器>'` 放后台，回执先落地。
- 重启前后各看一次 `docker ps` 的 `Up` 时长，确认真的重启了。

## 七、坑

- `hermes -z "..."` 的墙钟含 ~3s 启动开销；它只代表 cron / 一次性调用，**不代表常驻网关延迟**，别混用。
- 直接改 `/opt/data/config.yaml` 会被安全策略拒（`Refusing to write to Hermes config file`），一律走 `hermes config set`。
- 会话库 `state.db` 的 `messages.timestamp` 是 **unix 浮点秒**，不是 ISO 字符串；按 `user → 该轮最后一条 assistant` 求差才是单轮耗时。
- `state.db` 里同一句问题的多轮耗时会从 8s 跳到 83s，**它不能当基准**，只适合找异常尖峰；基准一律用 `date +%s%N` 墙钟。
