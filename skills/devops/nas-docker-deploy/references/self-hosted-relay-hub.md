# 自建 relay（hub）+ 多设备接线

适用场景：第三方 agent 栈默认把「设备间路由」放在厂商云端，BOSS 要求「不经过厂商云」时，
在 NAS 上自建 relay，再用组网（节点小宝）让手机/电脑接进来。
以 nanoMuse（`nano-muse/nanoMuse`）为例，机制对其他「云端 hub + 客户端 App」架构通用。

## 一、先分清三个角色（分不清就会白部署）

| 角色 | 是什么 | 能碰什么 |
|---|---|---|
| runtime（`<cli> serve`，如 8787） | 某台机器上的大脑 + 手 | 它所在机器的 shell / 浏览器 |
| relay（`cloud/`，`nanomuse_cloud`） | 总机：账号、设备目录、消息路由、模型代理 | 不碰任何屏幕，只转发 |
| 手机 App | 唯一能碰手机屏幕的手（Android `AccessibilityService`） | 手机上的 App、屏幕、通知 |

判据一句话：**问「BOSS 要它碰什么」**。要碰手机 → 必须装 App；只是不想走厂商云 → 装 relay。
只装 runtime 是第三种东西，别把它当成前两者的替代。

## 二、relay 部署（无 TLS，LAN / 组网内）

上游自带 `cloud/docker-compose.yml` + `docker-compose.local.yml`（local = 无 TLS、绑 `0.0.0.0`），
**直接用 override，别自己写 compose**。

`.env` 关键项（600，放 `cloud/.env`）：

```
RELAY_BIND=0.0.0.0
RELAY_PORT=<空闲端口>            # 8787/8788/8790/8791 在本 NAS 常被占，relay 用 8795
PUBLIC_BASE=http://<组网IP>:<端口>
CODE_SENDER=log                  # 验证码进日志，不依赖 SMTP/SMS
SIGNUP_OPEN=1                    # 建完第一个号立刻改 0 并填 ALLOWED_IDENTIFIERS
ALLOWANCE_CNY=0                  # 0 = 不限量
IMPROVE_DEFAULT=0                # 关掉「帮助改进模型」上报
UPSTREAM_BASE=http://192.168.199.2:20128/v1
UPSTREAM_KEY=<从 /opt/data/.env 读，绝不上命令行>
CLOUD_SECRET / CLOUD_ADMIN_TOKEN = secrets.token_hex(...)
CLOUD_MODELS=<见第三节>
```

启动与数据目录：

```bash
cd /volume2/2-AI/<app>/cloud
sudo -n docker run --rm -v .../cloud/data:/d alpine chown -R 10001:10001 /d   # 容器 uid 10001
sudo -n docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

- 启动日志里 `CODE_SENDER=log ... nobody receives them` 是**预期**的 ERROR，不是失败。
- 验收：`curl http://127.0.0.1:<端口>/healthz` → 200，但只是第一关，见第五、六节。

## 三、模型菜单必须做 id 映射

relay 内置菜单写死厂商 id（裸名如 `deepseek-v4.1-flash`），而 OmniRoute 只认带前缀的
`a2a/deepseek-v4.1-flash` → 客户端一发就 502 `upstream_model` / 上游 404。

`CLOUD_MODELS` 是 JSON 数组，每项是 ModelSpec，关键是 **`id`（App 看到并请求的）与 `upstream`（真实上游 id）分开**：

```json
[{"id":"deepseek-v4.1-flash","name":"DeepSeek V4.1 Flash","upstream":"a2a/deepseek-v4.1-flash",
  "input_modalities":["text","image"],"for":["chat"],"recommended":true,"recommended_for":["chat"],
  "price_in":0.0,"price_out":0.0},
 {"id":"qwen3.8-27b","name":"VL (屏幕)","upstream":"openrouter/nvidia/nemotron-3.5-super-vl:free",
  "input_modalities":["text","image"],"for":["gui","chat"],"recommended":true,"recommended_for":["gui"],
  "price_in":0.0,"price_out":0.0}]
```

- `for` 是 JSON 名，Python 侧叫 `for_`；值只能是 `chat` / `gui`。
- **每个 lane 必须恰好一个 `recommended_for`**，否则启动日志刷 `menu_warnings`（客户端默认模型会飘）。
- `gui` = 屏幕/Hands 用的视觉模型，必须挑上游**真能跑**的视觉 id（先 1-token 探活再写进菜单）。
- 改 `CLOUD_MODELS` 后 `docker compose up -d` 重建容器即生效，不用改镜像。

## 四、端到端验证（不做这步不算通）

顺序固定：

1. `POST /v1/auth/code {"identifier":"..."}` → **204 无 body**（`json.loads` 会炸，204 就是成功）
2. `docker logs cloud-relay-1 | grep -oE '[0-9]{6}' | tail -1` 取码（日志形如 `verification code for pr***@local.test (email): 123456`）
3. `POST /v1/auth/verify {identifier, code, device}` → 200，token 字段名是 **`api_key`**（不是 token/access_token）
4. `GET /v1/models`（Bearer api_key）→ 应等于 `CLOUD_MODELS` 的条数
5. `POST /v1/chat/completions` → 200 且**看正文**（返回「通道正常」这类真文本）

🔴 验证码 **TTL 很短**：取码与 verify 必须紧挨着做；先 request、再 grep 最后一条码，中间别插别的操作。
重复请求会生成新码，旧码立即作废 —— 报 `code_expired` 就是这一步超时了，重新走 1→3。

## 五、跨网可达性验证

从**另一台组网节点**（不是 NAS 本机）打：

```bash
ssh <另一节点> 'curl -s -m8 -o /dev/null -w "%{http_code}\n" http://<NAS组网IP>:<端口>/healthz'
```

- 本机 `127.0.0.1` 通只证明进程活着，**不证明组网能到**。
- 组网 IP 归属以 NAS 的 RouteAdd 日志为准（IP 会重排，别采信旧记录）。
- relay 重建容器后要**再验一次**，端口绑定随 compose 重建可能变化。

## 六、能力边界（回答「装了有啥用 / 能不能控手机」时的硬事实）

- 手机 App 里**没有 IM 渠道代码**；飞书/钉钉/企业微信/Telegram 是 Python 包 `nanomuse[channels]` 的功能，
  **只能跑在 runtime 上**，App 本身接不了飞书。
- relay 的 HTTP 只有 `GET /v1/devices`（列设备）和 `DELETE /v1/devices/{id}`（忘掉设备），
  **没有「派活」接口** —— 派活是设备之间走 WebSocket hub 协议的，外部程序调不进去。
- 因此「飞书发指令 → 家里手机干活」是三段链路：**飞书 → runtime(channels) → relay → 手机**，缺一段都不成立。
- runtime 操作手机只走 `PhoneLink`（Android App 的无障碍服务 / MobileGym 演示模块），
  **没有 ADB 通道**：容器内无 `adb`/`hdc` 二进制，源码里也无相关代码。想用 ADB 只能自己装二进制 + 走裸 shell，
  等于绕过它的 `phone_*` 工具和审批卡（敏感词拦截也没了）。
- 同一 IM 应用只能有一个长连接 → 给新栈配飞书入口必须另建 app_id/secret。
- iOS 没有对应无障碍权限 → 只能当指挥端，不能当手。

## 七、部署前先写清用途（否则装完就删）

装之前先回答三句：**谁用它、碰什么、BOSS 怎么触发**。写不出来就先问，不要「先装好再说」。
反例：装了 runtime 判「对当前任务无增量」删掉，随后 BOSS 问「能不能家里放台手机、飞书远程指挥」，
才发现那台 runtime 正是这条链路的必需中间层 —— 删早了，还要重装。
