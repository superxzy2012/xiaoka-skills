# 健康判据与告警设计（octop healthcheck 实测版）

适用：任何「定时探活 + 越界告警 + 状态落盘给对方核」的看门狗脚本。octop 这份是参考实现：
`/opt/data/bin/octop_healthcheck.sh`（探活+告警）、`/opt/data/bin/octop_expect.py`（阈值推导）。

## 1. 阈值必须从真相源推导，不能手写常量

```
GET /api/agents → 取 agent_id 去重计数 → 即 expect_agents
```

实测 17 = `main` 1 + 原 8（TAQG6V 9VQHTY Q8NY3B JF6ADQ X1N8RQ CMW4WR 4GK9GF XJWVMB）+ Agency 8（PRICE SUPPL GROW SEO WXGZH DOUY QA1 LOC）。

为什么不能写死：写死 `17` 时，下次加一个专家就变成「跑得好好的也告警」，减一个就变成「掉了一半还报绿」。
环境变量 `OCTOP_EXPECT_AGENTS` 只保留给测试，不能当默认值。

推导失败（登录不上、接口 500）→ 判 `expect_unreachable` 异常，**不要**回退到某个默认数字：
回退会让「探不到注册表」伪装成健康。

## 2. state 快照字段（给离线对端核）

`state/octop-health-alert.json`：

| 字段 | 含义 | 用途 |
|---|---|---|
| `status` | `ok` / `alert` / `recovered` | 一眼看当前态 |
| `ts_utc` | UTC 时间戳 | 人工对时，**不能当变更判据** |
| `ok` | `/api/health` 的 `ok` | 服务活着吗 |
| `agents_running` | health 报的在跑数 | 掉 agent 的唯一早期信号 |
| `expect_agents` | 注册表推导的应到数 | 与上一行比较 |
| `expect_source` | `registry` / `override` / `unreachable` | **这个数可不可信** |
| `expect_ids` | 参与计数的 id 全列 | 逐个人工复核，不用信我的口述 |
| `poll_daemon` | 守护进程数 | 30s 轮询还活着吗 |
| `problem` | 空=健康；非空=原因串 | 告警正文直接引用 |
| `health_raw` | 原始 health 响应 | 字段改名/新增时能回溯 |

`expect_source` 是这套设计的关键：对端不需要读脚本就知道 17 是推出来的还是人填的。

## 3. 三条硬规矩（每条都是踩出来的）

### 3.1 测试注入永不写共享审计通道

验告警态可以 `OCTOP_EXPECT_AGENTS=99 sh octop_healthcheck.sh`，但必须满足：

- override 只写**本地** state，`[ "$EXPECT_SOURCE" != "override" ]` 才允许 commit/push；
- 否则正本总线里会留下 `agents_running=17<99` 这种记录，对端只能追问「是不是把阈值调低了刷绿」。

**审计通道一旦被测试污染，真实告警也失去可信度。** 测试想留证据就写 `reports/` 说明或本地日志，不写 `state/`。

### 3.2 变更判据用指纹，不用时间戳

`ts_utc` 每轮都变 → 整文件比对或无条件 commit 会每 5 分钟产一条垃圾 commit，把真告警淹没。
指纹 = `status|agents|expect|source|daemon|problem`，存本地 `.octop_health_fp`，变了才推。

### 3.3 脚本快照上总线

判据脚本放在 NAS 本地（`/opt/data/bin/`），对端看不到。把快照 + 推导说明提交到总线 `reports/`：

```
reports/octop_healthcheck.sh
reports/octop_expect.py
reports/octop-health-expect-derivation.md
```

这样「阈值什么时候、被谁、改成什么」变成 `git diff`，而不是「你说是就是」。

## 4. 自证实验（交付时贴原文，不要只说「已生效」）

```bash
# ① 推导值
/opt/data/.venv-browser/bin/python /opt/data/bin/octop_expect.py
# → {"expect": 17, "source": "registry", "ids": [17 个]}

# ② 去抖：连跑两次，tip 不应变
T1=$(git -C /opt/data/a2a-bus rev-parse --short HEAD); sh octop_healthcheck.sh
T2=$(git -C /opt/data/a2a-bus rev-parse --short HEAD); echo "$T1 -> $T2"

# ③ override 隔离：注入后 tip 不应变
OCTOP_EXPECT_AGENTS=99 sh octop_healthcheck.sh; git -C /opt/data/a2a-bus rev-parse --short HEAD
```

## 5. 双通道告警

群消息会丢（人不在线、消息被刷走），state 文件不会。两条都要写：

- 群里：`⚠️【OCTOP:HEALTH】异常：<problem>｜health=<raw>｜<ts>`；
- 总线：`state/octop-health-alert.json`，恢复时写 `recovered` 覆盖（保留「曾经异常过」的痕迹）。

自动处置要保守：只拉起**自己的**守护进程（`pgrep -fc octop_a2a_daemon.sh` 为 0 时），不要顺手重启容器——
重启会断掉正在跑的 WS 问答，把「掉了个守护」升级成「用户正在用的服务断了」。
