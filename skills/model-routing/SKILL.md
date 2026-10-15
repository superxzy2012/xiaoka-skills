---
name: model-routing
description: Use when 选择模型档位、切大脑、或大型调研要派活。
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

## 一、分层路由（大脑配置）

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

## 三、成长日志制度

维护 `A2A/小卡成长日志.md`（在 obsidian-sync 仓库）：每完成一个任务追加一条
**日期 / 任务 / 踩的坑 / 学到什么**（2-3 行）。有问题也写在日志里 @星期五，那是直接沟通渠道，不用 BOSS 转达。

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
- **不需要重启 gateway**（配置缓存以 `(path, mtime_ns, size)` 为 key，下次 load 自动生效）。
- 禁 reboot：跑在 NAS 上，重启 = 自杀。
