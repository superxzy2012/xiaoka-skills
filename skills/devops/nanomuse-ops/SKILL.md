---
name: nanomuse-ops
description: Use when 部署/运维 nanoMuse 手机 agent 与自建 relay。
version: 1.0.0
author: 小卡
license: MIT
metadata:
  hermes:
    tags: [nanomuse, relay, android, docker, nas]
    related_skills: [nas-docker-deploy, nodebabylink-mesh-troubleshoot, omniroute-gateway-ops]
---

# nanoMuse 运维

## When to Use

- 部署、重启、排障 nanoMuse 的运行时（`serve`）或自建 relay（`cloud/`）。
- 用户问「nanoMuse 怎么操作我手机」「要不要经过浙大云端」「手机怎么连」。
- 要把 relay 模型菜单改到 OmniRoute 上真实可用的 id。

## 先分清三层，否则一定答错

| 层 | 是什么 | 能碰什么 |
|---|---|---|
| 飞书/聊天入口 | 话筒 | 只传文字 |
| `nanomuse serve` 运行时（默认 8787，容器 `nanomuse-app`） | 网页控制台 + 该机的工具 | **只碰它所在那台机器** |
| `cloud/` relay（本机 8795，容器 `cloud-relay-1`） | 只路由设备间的帧，不跑模型 | 不碰任何设备 |
| 手机 App | agent 跑在手机里 | 靠 Android `AccessibilityService` 才有「手」 |

**铁律**：部署在 NAS ≠ 能操作手机；接了飞书 ≠ 能操作手机。回答「怎么操作我手机」这类问题先讲清这三层，再给条件清单。

## 部署 relay（无域名、纯内网/组网、明文 HTTP）

1. 源码在 `/volume2/2-AI/nanomuse/cloud`，已有 `docker-compose.yml` + `docker-compose.local.yml`（本地无 TLS 覆盖层，正是给这种场景用的）。
2. 生成 `.env`（600），关键项：
   - `CLOUD_SECRET` / `CLOUD_ADMIN_TOKEN` 随机；`UPSTREAM_BASE=http://<OmniRoute>:20128/v1`；`UPSTREAM_KEY` 从 `/opt/data/.env` 读，**不要**写进命令行。
   - `CODE_SENDER=log`（验证码进容器日志，个人用不需要 SMTP/短信）、`SIGNUP_OPEN=1` 先放开、`IMPROVE_DEFAULT=0`、`HUB_ENABLED=1`。
   - `RELAY_BIND=0.0.0.0`、`RELAY_PORT=<空闲端口>`、`PUBLIC_BASE=http://<组网IP>:<端口>`。
3. **data 目录归属**：容器以 uid 10001 运行，宿主没有 `sudo chown`（本机 `sudo -n` 只放行 docker）→
   `sudo -n docker run --rm -v <path>/data:/d alpine chown -R 10001:10001 /d`
4. `sudo -n docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build`
5. 本机 `curl -o /dev/null -w '%{http_code}' http://127.0.0.1:<端口>/healthz` 应 200。

## 模型必须重映射（最耗时的坑）

relay 的 `DEFAULT_MODELS`（`nanomuse_cloud/config.py`）里 `upstream` 写的是**裸 id**，而 OmniRoute 只认带前缀的 id。不重映射就 `502 upstream_model ... 404 page not found`。

用 `CLOUD_MODELS`（单行 JSON 数组）整张覆盖菜单，`id` 是 App 看到的名字，`upstream` 是真实上游：

```json
[{"id":"deepseek-v4.1-flash","name":"DeepSeek V4.1 Flash","upstream":"a2a/deepseek-v4.1-flash","input_modalities":["text","image"],"for":["chat"],"recommended":true,"recommended_for":["chat"],"price_in":0,"price_out":0},
 {"id":"qwen3.8-27b","name":"屏幕模型","upstream":"openrouter/nvidia/nemotron-3.5-super-vl:free","input_modalities":["text","image"],"for":["gui","chat"],"recommended":true,"recommended_for":["gui"],"price_in":0,"price_out":0}]
```

- `for` 是 lane 列表（chat/gui）；**每个 lane 必须恰好一个 `recommended_for`**，否则启动日志告警、App 默认模型乱选。
- `gui` 那条是 Hands 读屏用的，必须视觉模型；`qwen3.8-*` 这类原厂 id 在 OmniRoute 上通常不存在，换 `nemotron-3.5-super-vl:free` 一类。
- 写进去之前先 `POST /chat/completions` + `max_tokens=1` 探活：**列表里有 ≠ 能用**（404/502/429 很常见）。

## 端到端验收（只看 healthz 等于没验）

`scripts/relay_e2e.py` 一条脚本跑完：取码 → 登录 → 列模型 → 真跑一次 chat。要点：

- `POST /v1/auth/code` 返回 **204 No Content**，没有 body —— 解析必须容错，否则 `JSONDecodeError`。
- 验证码从日志取：`docker logs cloud-relay-1 | grep -oE '[0-9]{6}'`（`CODE_SENDER=log`）。
- **码的 TTL 很短**：取码和验证必须同一脚本连着做，隔几分钟再验就是 `code_expired`。
- `POST /v1/auth/verify` 返回的凭据字段叫 **`api_key`**，不是 `token`/`access_token`。
- 之后 `Authorization: Bearer <api_key>` 调 `/v1/models`、`/v1/chat/completions`。

## 对外：走组网而不是公网

- 只绑 TCP。从另一台组网机器 `curl http://<NAS组网IP>:<端口>/healthz` 验证，**不要 ping**（relay 模式下 ICMP 不通，ping 不通不代表没通）。
- 组网 IP 会重排，以 NAS 侧 `NodeBabyLinkService.log` 的 `RouteAdd` 行为准。
- 明文 HTTP 是可用的：Android `usesCleartextTraffic=true`、iOS `NSAllowsArbitraryLoads` 都已开，App 登录页「使用其他服务器 / Use a different server」直接填 `http://IP:port`。

## 手机端能力边界

| 平台 | 能装 App | 有「手」 |
|---|---|---|
| Android 8+ arm64 | ✅ GitHub Releases 的 `nanoMuse-<ver>-arm64.apk` | ✅ 需在系统设置手动开无障碍 |
| iOS 13+ | ✅ TestFlight（链接在仓库 `docs/ios.md`） | ❌ 无对应权限，只能当指挥端 |
| 鸿蒙 NEXT（纯血） | ❌ 不跑 APK | ❌ 只能浏览器开 `http://IP:port/app` |
| 鸿蒙 4.x/5（安卓兼容） | ✅ | ✅ |

先问清对方手机的系统版本再承诺，别把「安卓能装」套到鸿蒙上。

## 安全与告知义务

- 首个账号注册完立刻 `SIGNUP_OPEN=0`，否则组网内任何人都能注册。
- 无障碍权限 = 能读整屏内容并点任意按钮（含微信/银行），装之前让用户自己确认，不要替他决定。
- 组网若是 relay 转发模式（NAS 侧无 tun 网卡），流量经第三方中继，加密但不过自家门；介意就换 WireGuard/Tailscale 直连。
- 接飞书要另建 app：**同一飞书应用只能有一个长连接**，与现有 Hermes 共用会抢连接、丢消息。
- 凭据一律走 `.env`/环境变量 + base64 管道落盘，不进命令行、不进聊天正文。
