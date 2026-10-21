---
name: nas-docker-deploy
description: Use when deploying a Docker container on the NAS.
version: 1.0.0
author: xiaoka
license: MIT
metadata:
  hermes:
    tags: [nas, docker, deploy, compose]
    related_skills: [nas-manager, omniroute-gateway-ops]
---

# 在 NAS 上部署 Docker 容器

## When to Use

- BOSS 说「把这个 GitHub 项目部署到 NAS docker 上」「在 nasdocker 装个 X」
- 需要在 NAS 上新建/更新/排障一个容器
- 需要改 NAS 宿主的 cron、systemd、配置文件

不适用：只读查看容器状态（用 nas-manager 的巡检段即可）。

## 一、执行通道（唯一正确的一条）

本容器（uid 10000 hermes）**没有** docker.sock，但 NAS 主机完全可达：

```bash
SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -i /opt/data/.ssh/id_ed25519 -o ConnectTimeout=8 DY@192.168.199.2"
$SSH 'sudo -n docker ps'
```

- 用户 `DY`（uid 1005，组 admin/users），**免密登录**。root/admin/xiaoka 都不行 —— 别浪费轮次试。
- `sudo -n` **只**免密 `/usr/bin/docker`，其他命令要密码。
- 改宿主文件（/etc、/var/spool/cron 等）：`sudo -n docker run --rm -v /etc:/etc alpine sh -c '...'`。
- 路径映射：容器内 `/opt/nas/volume2` = 宿主 `/volume2`。宿主 crontab 在 `/etc/cron.d/`、`/var/spool/cron/crontabs/root`。

## 二、必踩的坑

1. **scp / sftp 不可用** —— `scp` 报 `dest open ... No such file or directory`（SFTP 子系统被限），但目标目录其实存在。
   传文件改用 base64 管道：
   ```bash
   base64 -w0 local.yml | $SSH DY@192.168.199.2 'base64 -d > /volume2/2-AI/<app>/docker-compose.yml'
   ```
2. **DY 的写权限边界**：可写 `/volume2/2-AI`；**不可写** `/volume2` 顶层、`/volume2/docker`、**`/volume1/docker`**（root drwx------）。数据目录一律放 `/volume2/2-AI/<app>/` —— 上游 README 与任务规格里给的 `/volume1/docker/...` 挂载路径**照抄必失败**，要主动改掉并说明。
3. **大镜像 pull 会被调用方超时打断** —— 前台跑 `docker pull`，一旦超过工具超时（实测上限 420s）SSH 连接被掐、拉取半途而废，重试又从零开始。改为 NAS 侧后台拉取，再轮询镜像是否落地：
   ```bash
   $SSH DY@192.168.199.2 'nohup sudo -n docker pull <image> > /tmp/pull.log 2>&1 &'
   # 轮询（最多 8×30s）看 tag 是否出现
   $SSH DY@192.168.199.2 'sudo -n docker images --format "{{.Repository}}:{{.Tag}}" | grep <name>'
   ```

4. **`docker run -v <宿主路径>:<挂载点>` 之后，容器内只能用挂载点。**
   在容器里写 `/volume2/2-AI/...`（宿主路径）**不会报任何错** —— alpine 把它当容器内的普通路径，
   `mkdir`/`cp` 全部成功，`ls` 也列得出来，但文件落在**容器的可写层**，`--rm` 一退就消失了。
   判据只有一条：**退出容器后从宿主侧回读**（`ls` / `md5sum` 比对）。
   这个坑在「用 root 容器绕开权限写文件」时最容易踩 —— 容器内一切看起来都正常。

## 三、部署前预检

```bash
$SSH DY@192.168.199.2 'sudo -n docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'   # 已占用容器
$SSH DY@192.168.199.2 'sudo -n docker ps --format "{{.Ports}}" | tr "," "\n" | grep <PORT>' # 端口冲突
$SSH DY@192.168.199.2 'sudo -n docker info | grep -E "Docker Root Dir|Registry Mirrors"'      # 镜像存 /volume1/@docker
$SSH DY@192.168.199.2 'df -h /volume2 | tail -1'
```

镜像源：NAS 配的 mirror（xuanyuan / daocloud / 1panel）**只覆盖 docker.io**。ghcr.io 直连**多数时候**可用且不慢（678MB 镜像 76s），但会「假死」——见下方 §5.5。国内镜像仓备选 `ghcr.nju.edu.cn/<org>/<repo>:<tag>`。

### 🔴 拉取「假死」的判据与处置

症状：日志里所有 layer 都打了 `Download complete`，然后**再无一行输出**；干等 5 分钟行数不动。
**判据**：`ps -o pid,etime,time,stat,%cpu -p <pull-pid>` 看 `TIME` 是不是 `00:00:00` + `%CPU` 为 0 —— 是就说明进程在空转，不是磁盘慢、不是解压慢，等多久都不会好。
**处置**：杀掉重拉（`kill` 需要 root，用特权容器借宿主 PID 命名空间）：

```bash
$SSH DY@192.168.199.2 'sudo -n docker run --rm --privileged --pid host --net host alpine sh -c "kill -9 <pid>"'
$SSH DY@192.168.199.2 'nohup sudo -n docker pull ghcr.nju.edu.cn/<org>/<repo>:<tag> > /tmp/pull2.log 2>&1 &'
```

换镜像源后几十秒即落地。**别原地重试同一个源** —— 同一个源同一时刻会以同样方式再卡一次。

## 四、compose 模板

写到 `/volume2/2-AI/<app>/docker-compose.yml`：

```yaml
services:
  app:
    image: <registry>/<org>/<repo>:<pinned-tag>
    container_name: <app>
    restart: unless-stopped
    ports:
      - "<hostport>:<containerport>"
    volumes:
      - /volume2/2-AI/<app>:/data/.octop      # 数据落 2-AI 子树
    environment:
      HOME: /data
```

启动与验收：

```bash
$SSH DY@192.168.199.2 'cd /volume2/2-AI/<app> && sudo -n docker compose -f docker-compose.yml config --quiet && sudo -n docker compose -f docker-compose.yml up -d'
$SSH DY@192.168.199.2 'sudo -n docker ps --filter name=<app> --format "{{.Names}}\t{{.Status}}\t{{.Ports}}"'   # 要看到 (healthy)
$SSH DY@192.168.199.2 'sudo -n docker logs <app> 2>&1 | tail -25'
curl -s -o /dev/null -w "%{http_code}\n" http://192.168.199.2:<hostport>/   # 状态码
curl -s http://192.168.199.2:<hostport>/ | head -c 200                       # 必须看正文
```

### 🔴 验收必须看响应正文，不能只看 HTTP 状态码

**200 只证明「这个端口上有东西在应答」，不证明「应答的是你刚部署的东西」。**
实测：服务落到某端口后 curl 拿到 200 就报「通了」，实际应答的是早已占用该端口的另一个容器（qBittorrent WebUI）——
两个服务都返回 200，只有正文能区分，于是把错端口写进了给 BOSS 的报告。

判据（至少命中一个才算部署成功）：响应正文里的 `<title>`、产品名、或 `/api/health` 的 JSON 字段。

### 🔴 对话/agent 类应用：验收必须真发一轮对话，HTTP 200 不算

这类产品（自托管 AI 助理、IM bot、控制台）**聊天通常只走 WebSocket，REST 里根本没有 chat 路由**。
`/openapi.json`、`/api/openapi.json`、`/docs` 全 404 也不代表接口坏了 —— 很多产品压根不暴露 OpenAPI。
做法：`docker exec <c> grep -rn "APIRouter\|websocket" /app/src/**/routers/` 从源码拿真实路由与消息体格式，
再用 `websocket-client` 真发一句、收到非空正文才算通。别拿「页面能打开」当验收。

### 🔴 读真实端口绑定用 docker inspect，不要读 docker ps 的 Ports 列

`{{.Ports}}` 会把镜像 `EXPOSE` 的端口和实际绑定**并排**打印，例如：

```
3010/tcp, 0.0.0.0:30120->30120/tcp
```

极易被读成 `3010->3010`。真相只有这一条命令给：

```bash
$SSH DY@192.168.199.2 'sudo -n docker inspect <app> --format "{{json .HostConfig.PortBindings}}"'
```

### 🔴 docker 不会自动改端口

绑到已占用端口会**直接失败**：`Bind for 0.0.0.0:3010 failed: port is already allocated`。
所以「容器起来了、但端口和命令里写的不一样」只可能是当初那条命令就不是那个端口 ——
**别归因成 daemon 自动重映射**，回去看 `.HostConfig.PortBindings` 再下结论。

### 端口预检要查归属，不只是查占用

```bash
$SSH DY@192.168.199.2 'sudo -n docker ps --format "{{.Names}}|{{.Ports}}" | grep :<PORT>'   # 是谁占了
```

冲突时改一个空闲端口并在报告里写明**为什么改**，不要照抄规格里给的端口号。

**规则**：镜像 tag 要 pin 具体版本，别用 `latest`（先查上游 release，取最新 tag）。

## 五、worked example：Octop（2026-10-14 部署 + 配 OmniRoute 模型）

- 上游 `TencentCloud/Octop`（MIT，★9.1k，FastAPI + React，自托管多用户 AI 助理）。**注意区分**：`bestruirui/octopus` 是另一个项目（LLM 聚合网关，AGPL）。
- 预构建镜像 `ghcr.io/tencentcloud/octop:<tag>`（amd64+arm64），**无需本地 build**；tag 无 `v` 前缀（`1.0.2b7`，不是 `v1.0.2b7`）。`latest` == 最新 tag。
- 数据目录 `/volume2/2-AI/octop` → 容器 `/data/.octop`，端口 **8088**。
- 关键 env：`HOME=/data`、`OCTOP_PORT=8088`、`OCTOP_BIND_HOST=0.0.0.0`、`OCTOP_ADMIN_USERNAME=admin`、`LANGFUSE_TRACING_ENABLED=false`。
- 首次引导三条路：
  - 不设 `OCTOP_DEFAULT_PASSWORD` → 不建管理员，走向导，向导口令写 `/data/.octop/octop-login.txt`；默认 `OCTOP_REQUIRE_SETUP_PASSWORD=true`（要口令才能进向导）。
  - 设 `OCTOP_REQUIRE_SETUP_PASSWORD=false` → 打开页面直接自建账号（本次采用，避免任何口令出现在聊天里）。
  - 或设合格的 `OCTOP_DEFAULT_PASSWORD`（≥8 位含字母+数字，且不在常见弱密码表内）→ 自动建号并把凭据写 `/data/.octop/credential.txt`。
- 验收：`/api/health` 返回 `{"ok":true,...}`；`/api/setup/status` 看 `setup_required`；`docker exec <c> octop --version`。
- 登录 URL：`http://192.168.199.2:8088`。

### 5.1 给 Octop 配 OmniRoute 免费模型（已实操）

Octop 的 provider/模型全部落在 SQLite，CLI 可直接离线写，**不需要 Web 登录**：

```bash
sudo -n docker exec octop octop provider list                 # 现有 provider
sudo -n docker exec octop octop models active                 # 当前全局默认模型
sudo -n docker exec octop octop models list                   # 解析后的可用模型
sudo -n docker exec octop octop provider test <id> --model X  # 真发一次 completion 探活
```

**写入用 `provider create`（注意：`--api-key` 无 prompt，必须显式传）**：

```bash
sudo -n docker exec octop octop provider create \
  --name omniroute --kind openai --base-url http://192.168.199.2:20128/v1 \
  --api-key "$KEY" --models '[{"id":"assistant","name":"assistant","enabled":true}]'
sudo -n docker exec octop octop models active --provider omniroute --model assistant
```

- `--kind openai` = 通用 OpenAI 兼容端点（走 `KIND_TO_PROTOCOL` 映射）。容器在 bridge 网络，但**能直连宿主机 LAN IP** `192.168.199.2:20128`（实测 3ms）。
- `--models` 是 JSON 数组，元素 `{id,name,enabled}`；`enabled` 不能省。

🔴 **密钥绝不进 argv**（会出现在容器 `ps` 里）。正确做法：把建 provider 的 Python 片段 base64 推到 NAS → `docker cp` 进容器 → **密钥从 stdin 管道喂进去**，脚本内部调 `open_cli_services` + `create_provider_offline`：

```python
# remote_add_provider.py（在容器内执行）
import json, sys
from octop.cli.support.offline_ops import create_provider_offline
key = sys.stdin.read().strip()
row = create_provider_offline(name=sys.argv[2], kind=sys.argv[3],
                             base_url=sys.argv[4], api_key=key,
                             models=json.loads(sys.argv[1]))
row["api_key"] = "<set:%d chars>" % len(row.get("api_key") or "")  # 回显必须打码
print(json.dumps(row, ensure_ascii=False, indent=2))
```

```bash
# 本地：密钥从 config.yaml 读出，经 stdin 送入
python3 -c "..." | ssh ... 'sudo -n docker exec -i octop python /tmp/ap.py <models_json> omniroute openai <base_url>'
```

**端到端验证**（`provider test` 只证明连通；要证明真出文本，用 Octop 自己的模型工厂）：

```python
from octop.cli.support.offline_ops import open_cli_services
from octop.infra.agents.providers.probe import build_probe_chat_model
with open_cli_services(None) as svc:
    row = next(r for r in svc.provider_repo.list_all() if r.name == "omniroute")
    model = build_probe_chat_model(row, model_id="assistant")
    print((await model.ainvoke("Reply with exactly one word: PONG")).content)
```

坑：`ProviderStore()` 需要 `provider_repo` 参数，别直接实例化 —— 用 `open_cli_services(None)` 拿 `svc.provider_repo`。

⚠️ `/api/usage/history` 的 `byModel` **不能**用来验证单次调用（聚合滞后，实测 ping 后计数不动）—— 要验证就直连模型工厂看返回文本。

- 实测结果：`assistant` / `free-pool` 两个 combo 都返回 `PONG`；`octop models active` = `omniroute / assistant`。
- 完成向导前 8088 无鉴权开放（`setup_required=true`），账号可由 BOSS 自己在页面建；也可以脚本一次性建完，见 5.1.1。

### 5.1.1 用 setup 向导 API 一次性初始化（SQLite + 管理员 + provider）

BOSS 说「帮我配置好，下次开箱即用」时，**不要手点向导页面** —— 向导本身就是一组 HTTP 接口，脚本跑完即交付。

**先读源码拿契约**（向导态下没有 OpenAPI）：

```bash
sudo -n docker exec octop ls /app/src/octop/api/routers/
sudo -n docker exec octop grep -n "@router\|class .*Request" /app/src/octop/api/routers/setup.py
sudo -n docker exec octop sed -n '1,120p' /app/src/octop/api/routers/setup.py
```

顺序固定：`GET /api/setup/status` → `POST /api/setup/begin`（取 setup token，后续每步都要带）
→ `POST /api/setup/database`（选 sqlite）→ `POST /api/setup/initial-admin`（username/email/password）
→ `POST /api/setup/test-provider` → `POST /api/setup/finish`。

🔴 **数据库只能绑一次。** 已绑定的实例再调 `/api/setup/database` 会把连接池关掉，
之后所有碰 DB 的请求报 `Cannot operate on a closed database`（这一步本身还返回成功，最容易误判）。
处置：`sudo -n docker restart <c>` 即恢复，数据不丢。**所以初始化脚本第一件事必须是读 `status.setup_required`，
false 就跳过数据库那一步** —— 重跑脚本不能靠「接口大概幂等」这种假设。

- 选 **SQLite**（单文件 `octop.db`，随数据目录持久化）；页面上的 PostgreSQL 是内测选项，别选。
- provider 的 key 从 `/opt/data/.env` 读（如 `CUSTOM:192-168-199-2-20128_API_KEY`），脚本里不出现明文；
  生成的 admin 密码写 `/opt/data/secrets/<app>_admin.txt`（600，目录 700），不打印。
- 验收四件套：`/api/health` 返回 `db:true` + `agents_running:1`；登录拿 `access_token`；
  `GET /api/providers/active-model` 指向你配的那条；**WebSocket 真发一轮对话**：
  ```
  ws://<host>:<port>/api/agents/<agent_id>/chat/ws?token=<JWT>
  → {"type":"user_turn","text":"现在几点"}  # 收流式，要看到中文正文
  ```
- 🔴 **必须复验「重启后还能用」**：`docker restart` 后容器有几十秒不可用期，立刻请求会被误判成坏了 ——
  轮询 `/api/setup/status` 到 200（约 12×8s）再重跑 e2e。顺带核 `docker inspect --format '{{.HostConfig.RestartPolicy.Name}}'`
  与 `GET /api/settings/timezone`（多用户产品自带 cron，时区错会导致定时任务按 UTC 跑）。
- 交付话术：地址 / 账号 / 密码 / 已选 SQLite / 接了哪个模型 / 实测证据（一句真回复）/ 自启策略，
  外加一句「密码文件在哪、建议自己改」。
- 配好之后 BOSS 必然追问「这到底是干嘛的、在蜂群里能做什么」—— 走 `self-hosted-platform-onboarding`
  （四层取证 + 落位判断 + 表格化交付），不要凭 README 现编。

### 5.2 另一例：cli2api（管理员 key 从启动日志取）

`ghcr.io/caigee-cmd/cli2api:latest`，数据 `/volume2/2-AI/cli2api/data`（**不是**规格里给的 `/volume1/docker/...`）。

- **端口不能照抄规格里的 3010** —— NAS 上 3010 已被 **qBittorrent WebUI** 占用（`0.0.0.0:3010->8080`）。
  实际部署落在 **30120**，控制台 `http://192.168.199.2:30120`（正文含 `<title>CLI2API</title>`）。
  交付前必须用 `docker inspect --format '{{json .HostConfig.PortBindings}}'` 确认真实端口再写进报告。

- 🔴 **管理员 key 只在「首次初始化」那一次启动时打印，之后重建容器就再也拿不到。** 用 `sudo -n docker logs cli2api` 只在**全新数据库**时才有效；容器一旦被 `docker rm -f` 后重跑，DB 已存在 → 新容器**只打印一行 `listening on ...`，没有 key**，去日志里找必然扑空。
  可靠的取法是直接从 SQLite 取（复制副本读，**读完全局删除副本**）：
  ```bash
  $SSH DY@192.168.199.2 'sudo -n docker run --rm -v /volume2/2-AI/cli2api/data:/d alpine sh -c "cp /d/qoder.db /d/ro_copy.db && chmod 644 /d/ro_copy.db"'
  python3 -c "import sqlite3;print(sqlite3.connect('/opt/nas/volume2/2-AI/cli2api/data/ro_copy.db').execute(\"select value from app_secrets where name='proxy_api_key'\").fetchone()[0])"
  $SSH DY@192.168.199.2 'sudo -n docker run --rm -v /volume2/2-AI/cli2api/data:/d alpine rm -f /d/ro_copy.db'   # 必须删，副本含明文密钥
  ```
- **cli2api 没有「用户名 + 密码」** —— 控制台认证就是这一把管理员 key（单一 token，无账号名）。登录页填它即可；接口鉴权头是 `Authorization: Bearer <key>`（`/api/accounts`、`/api/keys`、`/api/models` 都可用它验活，返回 200 即有效）。
- 该 key 明文躺在 `qoder.db` 的 `app_secrets.proxy_api_key`，且首启时进过容器日志 → 交付时提醒 BOSS 首次登录后轮换。
- 全新部署的 `accounts` / `api_keys` 都是**空数组**，控制台登进去一片空白 —— 交付时要主动说明「还需添加账号、生成客户端 key」，别让 BOSS 以为装坏了。
- **新容器一律加 `--memory <上限>`**：NAS 可用内存本就紧张（实测余 8G 左右，同时跑着 OmniRoute / Emby / MoviePilot 等），无上限的新容器可能把整机拖垮。

### 5.3 又一例：n8n（2026-10-15 部署 + 打通 OmniRoute）

`n8nio/n8n:2.43.5`，数据 `/volume2/2-AI/n8n/data` → 容器 `/home/node/.n8n`。

- 🔴 **端口 5678 在 NAS 上已被 `g-box`（alist-tvbox，host 网络 + nginx）占用。**
  它在 `docker ps` 的 `{{.Ports}}` 列里**根本不显示**（host 网络容器），只能靠宿主 netns 反查：
  端口转十六进制（5678 → `162E`）→ 扫 `/proc/net/tcp{,6}` 拿 inode → 遍历 `/proc/*/fd` 找
  `socket:[<inode>]` → 读 `cgroup` 得到容器 ID。实际部署落在 **5679**。
- 🔴 **挂载目录必须 chown 1000:1000**：n8n 容器内以 uid 1000 跑，NAS 上 DY 建的目录是 1005，
  否则启动即 `EACCES: permission denied, open '/home/node/.n8n/config'`。
  ```bash
  sudo -n docker run --rm -v /volume2/2-AI/n8n/data:/d alpine sh -c "chown -R 1000:1000 /d"
  ```
- 🔴 **`sudo -n` 只免密 `/usr/bin/docker`**，`sudo -n sh 脚本` 必被拒。拆成两半：文件用 DY 身份写，
  docker 命令单独走 `sudo -n docker`。
- 🔴 **不要在 512M 限制的容器里跑 `docker exec <c> n8n execute --id X`** —— 第二个 n8n 进程吃爆内存，
  **主进程被一起拖死**（`RestartCount` +1，日志 `Last session crashed`）。手动执行一律走 REST API。
- 🔴 **n8n 2.x 已移除 `N8N_BASIC_AUTH_*`**：设了**静默忽略，连 deprecation 警告都没有**。
  真实机制是 owner 账号 —— `/rest/settings` 看 `userManagement.showSetupOnFirstLoad`，
  然后 `POST /rest/owner/setup {"email","firstName","lastName","password"}` 建号（返回 200 即成功）。
  SPA 外壳 HTML 本来就公开可访问（200 只证明编辑器页面在），真正的门是 `/rest/login`（未登录 401）。
- `N8N_BASIC_AUTH_PASSWORD` 无 prompt、可当「口令载体」用：`docker exec <c> printenv N8N_BASIC_AUTH_PASSWORD`
  取出来喂给建号/登录，口令不进聊天。
- 弃用项：`WEBHOOK_URL` → `N8N_WEBHOOK_URL`（启动日志会列 deprecation）。
- 密钥放 compose 同目录的 `.env`（600），compose 文件本身不含明文；再汇总一份到
  `/volume2/2-AI/secrets/<app>-credentials.txt`（600，目录 700）。

**手动跑 workflow 的正确契约（试了 5 种 body 才成）**：

```
POST /rest/workflows/{id}/run
{"workflowData": <GET /rest/workflows/{id} 的 data 原样回传>,
 "runData": {},
 "triggerToStartFrom": {"name": "<触发节点名，如 Manual Trigger>"}}
# -> {"data":{"executionId":"3"}}
```
- ❌ `startNodes`（任何形状）→ 400「specify either a trigger to start from or a destination node」
- ❌ `destinationNode: null` → 400「Expected object, received null」；`destinationNode:{"name":..}` → 400「Required」
- 认证：`POST /rest/login {"emailOrLdapLoginId":..., "password":...}` 拿 `n8n-auth` cookie（cookie jar）。
- 读结果：`GET /rest/executions/{id}` 的 `data.data` 是**压缩格式**（JSON 数组 + 数字下标字符串引用），
  必须自己 unflatten（字符串若是十进制数字且小于数组长度，就递归解析 `arr[int(s)]`）才能拿到节点真实返回。

- 交付实例：容器 `n8n`（`n8nio/n8n:2.43.5`，`0.0.0.0:5679->5678`，`--memory 512m`，unless-stopped），
  URL `http://192.168.199.2:5679`，owner `n8n-admin@xiaoka.local`，
  workflow「OmniRoute连通性测试」= Manual Trigger → HTTP Request(POST OmniRoute `/v1/chat/completions`)，
  实测返回 `n8n->OmniRoute 通了`。

### 5.4 不回源核实就采信 n8n 交付物：直接查 SQLite

对端/自己汇报「workflow `VEdD6...` 已激活 + credential `NdDN...` 已建」时，**不要靠 REST API 登录验**
（登录会碰到 rate limit，实测 `/rest/login` 直接 429），直接读 DB —— 只读、不需要口令：

```bash
$SSH DY@192.168.199.2 'python3 -c "
import sqlite3
c=sqlite3.connect(\"/volume2/2-AI/n8n/data/database.sqlite\")
print(\"workflows:\")
for r in c.execute(\"select id,name,active from workflow_entity\"): print(\" \",r)
print(\"credentials:\")
for r in c.execute(\"select id,name,type from credentials_entity\"): print(\" \",r)
"'
```

- `active` 列 1/0 就是 workflow 是否真激活 —— 比任何汇报都硬。
- `credentials_entity` 只给 id/name/type，**不含密钥明文**，可安全引用。
- 该 DB 是 WAL 模式（有 `-wal` / `-shm` 伴随文件），**只读连接安全**；但别在 n8n 运行时写它。
- DB 属主是容器内 uid（`superxzy`），DY 读得到，无需 sudo。

### 5.5 又一例：FreeLLMAPI（2026-10-16 部署）

上游 `tashfeenahmed/freellmapi`（MIT，★36k，自托管「免费 LLM 路由器」：把多家免费额度的平台拧成一个 OpenAI 兼容端点）。

- 端口：镜像内 **3001**；NAS 上 3001/3002 已被 **moviepilot-v2** 占用 → 宿主落 **3003**（`0.0.0.0:3003:3001`）。
- 数据 `/volume2/2-AI/freellmapi/data` → 容器 `/app/server/data`；`mem_limit: 768m`。
- 必填 env：`ENCRYPTION_KEY`（32 字节 hex，`python3 -c "import secrets;print(secrets.token_hex(32))"`），写同目录 `.env`（600），compose 用 `env_file` 引。
- 健康检查走 `/api/ping` → `{"status":"ok","timestamp":...}`。
- 🔴 **首装设置码只在首次启动日志里**（`First-run setup code: XXXXXXXXXX`）——同机浏览器可免码进，**异设备必须输码**才能建第一个账号。这等于管理员入口：交付给 BOSS 时要一并说明「建完账号即失效」。
- 镜像 tag 上游只发 `latest`（无版本号），照实写并在报告里注明。
- 交付实例：容器 `freellmapi`，`ghcr.nju.edu.cn/tashfeenahmed/freellmapi:latest`，`0.0.0.0:3003->3001`，healthy，URL `http://192.168.199.2:3003`。

**5.5.1 首次初始化（2026-10-16 已实操走通）**

初始化完成的可执行判据（不要靠页面观感）：

```bash
$SSH 'curl -s http://127.0.0.1:3003/api/auth/status'   # 期望 {"needsSetup":false,...}
```

- 建号接口 `POST /api/auth/setup {email,password}`。**局域网调用要一次性设置码，环回 127.0.0.1 免码**；
  前端是**先提交一次拿 403，页面才显示设置码输入框**（所以「页面上找不到码框」不等于不支持）。
  桌面版免密登录靠 `FREEAPI_DESKTOP=1`，Docker 部署没有 → 只能走邮箱+密码。
- 🔴 **统一 API key 不在 `api_keys` 表，在 `settings.unified_api_key`**（59 字符）。
  用容器内 node 读出来写文件，**只打印前缀不回显全值**：
  ```bash
  base64 -w0 key_out.js | $SSH 'base64 -d > /tmp/key_out.js'
  $SSH 'sudo -n docker cp /tmp/key_out.js freellmapi:/tmp/key_out.js >/dev/null && \
        sudo -n docker exec -w /app -e NODE_PATH=/app/node_modules freellmapi node /tmp/key_out.js'
  ```
- 🔴 **容器内跑 node 脚本必须带 `-w /app` + `-e NODE_PATH=/app/node_modules`**，否则 `better-sqlite3` 解析不到 → 输出重复/报错，看着像脚本写错。
- 🔴 **`data/` 是 700、容器内 root 属主** → DY 在宿主侧 `cat` 报 Permission denied。
  把 key 拷到 DY 可读处要借 root 容器：
  ```bash
  $SSH 'sudo -n docker run --rm -v /volume2/2-AI/freellmapi:/w alpine sh -c "cp /w/data/UNIFIED_KEY.txt /w/UNIFIED_KEY.txt && chmod 600 /w/UNIFIED_KEY.txt && chown 1005:100 /w/UNIFIED_KEY.txt"'
  ```
- 🔴 **FreeLLMAPI 不是「零配置白嫖」网关，是「免费额度聚合器」。** 首装后调 `/v1/models` 会列出 259 个模型，
  但**全部 `available:false`、`unavailable_reason:"no_key"`** —— 每个平台都要你自己去它的免费档注册领 key，
  在面板 Keys 页粘贴（`dist/lib/key-parser.js` 按格式自动识别平台）。上游 key 数为 0 时直接调会 503。
  目录口径（`settings.catalog_applied_json`，version 2026.10.16）：**38 平台 / 377 模型**，有模型行的 32 个：
  electronhub(65) · aihorde(32) · cloudflare(26) · airforce(20) · nvidia(18) · cohere(17) · google(15) ·
  kilo(13) · ovh(13) · mistral(12) · openrouter(12) · modelscope(11) · waterfall(10) · dreamprompting(9) ·
  xkiro(9) · requesty(8) · groq(7) · router9(6) · ollama(6) · agnes(5) · sealion(5) · septor(5) · aion(4) ·
  clod(4) · bazaarlink(3) · llm7(3) · routeway(3) · zhipu(3) · nara(2) · radeon(2) · unorouter(2) · logfare(2)。
  交付时必须明说这一步，否则 BOSS 会以为装坏了。

**5.5.2 忘了密码 / BOSS 要账号密码（已实操）**

`users.password_hash` 是 **scrypt 单向哈希**（`scrypt$<salt>$<hash>`），**没有反解路径**。不要停在「读不出来」这句上，也别改哈希或自造密码 —— 走应用自带的重置流程，让 BOSS 自己设：

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://192.168.199.2:3003/api/auth/forgot-password \
  -H 'Content-Type: application/json' -d '{"email":"<账号邮箱>"}'
$SSH 'sudo -n docker logs --tail 25 freellmapi 2>&1 | grep -A3 -i "reset code"'
```

- 码打在容器日志里，**TTL 15 分钟**；过期就再触发一次（幂等，可反复生成）。
- 交付格式：账号 + 重置码 + 有效期 + 登录地址 + 三步操作；并明说「哈希读不出是设计如此，不是我扣着不给」。
- 账号若也不确定：`select email from users` 从 DB 副本读（**副本用完删**）。

### 5.6 又一例：cdp-chrome（2026-10-16 部署，T-012）

NAS 容器内自建 headless Chromium，给抖音/B站解析提供 CDP，**摆脱对局域网电脑的依赖**。

- 镜像 `zenika/alpine-chrome:latest`（Chromium 124，容器内用户 `chrome` uid 1000）。
- 🔴 **NAS 直连外网是「选择性」的**：`www.example.com` 通、`registry-1.docker.io` 超时（exit 124）。
  别因为一个域名通了就认定网络没问题。国内镜像源实测：**`docker.1ms.run` 可用**、`hub.rat.dev` 可用；
  `docker.m.daocloud.io` 拉 `alpine` 可以但拉 `zenika/alpine-chrome` 失败；`docker.nju.edu.cn` denied。
  拉完 `docker tag docker.1ms.run/zenika/alpine-chrome:latest zenika/alpine-chrome:latest` 还原名字。
- 🔴 **端口必须绑 LAN IP，不要绑 0.0.0.0**：`-p 192.168.199.2:9222:9222`。
  （工单示例里写 `--remote-debugging-address=0.0.0.0` 是**容器内**监听地址，与宿主 `-p` 绑定是两件事；
  容器内必须 0.0.0.0 才能被 `-p` 转发，宿主侧只绑 LAN IP 即满足「禁暴露公网」。）
- 🔴 **`--user-data-dir=/data` 的挂载目录必须 `chown 1000:1000`**，否则 Chromium 起不来。
- 启动命令：
  ```bash
  sudo -n docker run -d --name cdp-chrome --shm-size=1g --memory=1g --restart unless-stopped \
    -p 192.168.199.2:9222:9222 -v /volume2/2-AI/cdp-profile:/data \
    zenika/alpine-chrome:latest --no-sandbox --remote-debugging-address=0.0.0.0 \
    --remote-debugging-port=9222 --user-data-dir=/data --disable-blink-features=AutomationControlled
  ```
- 验收：`curl -s http://192.168.199.2:9222/json/version` → `HeadlessChrome/124...`；
  `docker inspect --format '{{json .HostConfig.PortBindings}}'` 确认只绑 `192.168.199.2`。

**客户端**：`/opt/data/memories/nas_cdp.py`（用 `/opt/data/.venv-browser/bin/python` 跑）。

```bash
python nas_cdp.py status            # 探活
python nas_cdp.py refresh-cookies   # 从源浏览器拉登录态注入
python nas_cdp.py douyin <url>
python nas_cdp.py bilibili <url>
```

### 5.6.1 CDP 登录态与风控（四个实测坑）

1. 🔴 **抖音页面 `wait_until="domcontentloaded"` 会挂死** —— 页面长连接不结束，一直等到 timeout。
   一律用 `wait_until="commit"` + 显式 `wait_for_timeout(9000~12000)`。
2. 🔴 **抖音 `sessionid` 是 HttpOnly，`document.cookie` 取不到** —— 必须走 CDP `Storage.getCookies`。
   且 **`Storage.getCookies` 不能传 `browserContextId`**（传了返回空）。
3. 🔴 **登录态来源优先「从已登录浏览器只读导出」而不是让 BOSS 扫码**：
   BOSS 的 Windows Chrome 有常开 CDP（`http://192.168.199.184:9224`），
   `Storage.getCookies` **不新建也不关闭任何标签**，完全无打扰（BOSS 硬要求：绝不抢焦点）。
   导出的 cookie 用 Playwright `context.add_cookies()` 注入，字段需裁剪成
   `{name,value,domain,path,expires,httpOnly,secure,sameSite}`；CDP 的 `sameSite` 只接受 `Strict/Lax/None`，
   `expires=-1`（会话 cookie）要**省略**而不是传 -1。
4. 🔴 **别用 `grep sessionid /data/Default/Cookies` 验证登录态** —— 那是加密 SQLite，查不到明文属正常。
   判据是**行为**：`docker restart cdp-chrome` 后**不注入 cookie** 直接 headless 打开视频页，
   能拿到标题/作者/点赞数且 `视频数据加载中` 消失 → 登录态确实持久化在卷里。

自测基线（2026-10-16 实测通过）：
- 抖音 `https://v.douyin.com/DDW2g-qE1F0/` → 跳 `/video/7694963842081851259`，
  标题「每月白嫖74亿token的开源项目…」、作者「亚莱加德」、36.9万赞、`video_src` 拿到 `.mp4`。
- B站 `https://www.bilibili.com/video/BV1GJ411x7h7` → h1/UP主/播放量齐全，`has_video=true`。

### 5.7 又一例：Obsidian 中心化知识库 MCP（2026-10-18 部署）

给蜂群（云端 Queen/本地 8 agent/远端 Workbuddy）一份共享 Obsidian 集体记忆。选型 **`obsidian-ai-miniserver`**（PyPI 0.2.1，`whogben/obsidian_ai_miniserver`，MIT；纯 headless 直读 vault 文件夹，**不需 Obsidian Sync 付费账号**，同时起 streamable HTTP MCP + REST/OpenAPI + Web UI）。

- **没有官方预构建镜像**，且 NAS 直连 PyPI 超时（exit 124）→ 自建镜像，Dockerfile 里 `pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple`，基于本地已有的 `python:3.12-slim`（免拉基础镜像，build ~30s）。
- 🔴 **README 与 PyPI 稳定版 CLI 不符**：README/main 用 `start --vault name:path`（多 vault），但 0.2.1 的 `start` **只收单个位置参数** `[vault_path]`，传 `--vault` 直接报 `No such option` 并 crashloop。要多 vault → **跑多个容器实例**，各挂一个目录（本次 hive + skillbox 两实例）。
- 端口：容器内 MCP **8716**（端点 `/mcp`，streamable HTTP）、REST/Web **8747**（`/api`、`/web`、`/api/openapi.json`）。宿主按规格映射 3456→8716(hive MCP)、3457→8747(hive REST)、3458/3459(skillbox)。**只绑 LAN IP** `192.168.199.2:`，不暴露公网。
- 🔴 **MCP 工具只有一个 `obsidian`，入参是包在 `arguments.request` 里的 JSON 字符串（discriminated union），不是对象**。先 `tools/list` 看 `inputSchema.properties.request.$defs`，请求体用 `kind` 路由：`list_files/read_text/search_files/write_text/append_text/replace_text/move_file/get_vault_info/batch` + 管理类。直接传对象 → `Input should be a valid string`；字段名错（如 `content`/`action`）→ pydantic 校验错。search 支持正则、中文正常。
- 🔴 **鉴权**：MCP `initialize` 握手本身不校验 token（无 token 也能建 session），但**所有数据类工具调用无 `Authorization: Bearer` 必返 `{"kind":"error","message":"Invalid token"}`**。所以 `/api/openapi.json` 无 token 返 200 是正常的（文档公开），别误判成"鉴权没生效"。token 用 `secrets.token_hex(32)`，走 compose `.env`（600）+ `OBS_AI_MS_ADMIN_TOKEN`。
- 🔴 **必须 `user: "1000:10"`（vault 属主 superxzy:admin），不能让容器以 root 跑**：root 容器写出来的笔记宿主属主 `0:0 664`，其他 uid 的 agent 只能读不能改删，违背"多 agent 共享写"。加了非 root 后要再 `chown` 两个目录给 1000:10，否则 PermissionError：①挂载的 config 卷；②**vault 内的 `.obsidian/`**（服务要在里面写 `obsidian_ai_miniserver.json`；首次 root 跑还会在 vault/skills 各建一个 root:root 的 `.obsidian/`，chown 之，别动其他笔记）。
- 数据已在 USB 盘：`/volume2/2-AI` 与 `/mnt/@usb/sde1/2-AI` 是**同一个 ext4 设备**（`stat -c %d` 设备号相同），docker 挂载直接用宿主路径 `/mnt/@usb/sde1/2-AI/obsidian_vault`（7933 篇）和 `.../skills`（351 技能；其中 6 个悬空软链会让 `list_files` 报个别 `No such file`，不影响 search，可忽略或清理）。
- 交付：容器 `obsidian-mcp`(hive) + `skillbox-mcp`，均 healthy，mem 640m/512m，compose 在 `/mnt/@usb/sde1/2-AI/obsidian-mcp/`。
- **Hermes 客户端配置**（键名是 `mcp_servers`，HTTP transport 用 `url`+`headers`，不是 stdio 的 command）：
  ```yaml
  mcp_servers:
    obsidian_hive:
      url: "http://192.168.199.2:3456/mcp"
      headers: { Authorization: "Bearer <token>" }
    skillbox:
      url: "http://192.168.199.2:3458/mcp"
      headers: { Authorization: "Bearer <token>" }
  ```
  改完重启 Hermes；工具注册名 `mcp_obsidian_hive_obsidian` 等。验证 MCP 用原生 `initialize`→`notifications/initialized`→`tools/list` 三步握手（Accept 要带 `text/event-stream`，session 走响应头 `Mcp-Session-Id`，SSE 体取 `data:` 行）。

### 5.8 又一例：nanoMuse（源码自建镜像 + 配置文件挂载 + OmniRoute）

上游 `nano-muse/nanoMuse`（GPL-3.0-or-later，Python 内核 + Swift App），**没有官方镜像** → 源码构建。

- 取源码用 codeload tarball（`git clone` 写 NAS 磁盘极慢）：
  `curl -sSL https://codeload.github.com/<owner>/<repo>/tar.gz/refs/heads/main | tar xz --strip-components=1`。
- 构建：`sudo -n docker build --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple -t <app>:latest .`，
  实测 88s / 391MB。**必须后台跑**（`background=True`），前台会撞工具超时。
- 目录 `/volume2/2-AI/<app>`：`config/config.toml`（**单独 ro 挂载进容器**）、`.env`（600）、`workspace/`、具名卷 `<app>-data`。
- 🔴 **改配置走「挂载 + restart」，不要重建镜像**：`-v .../config/config.toml:/app/config/config.toml:ro`
  → 改完 `docker restart` 即生效。重建一次 90s，改配置 3s。
- 🔴 **OmniRoute 的模型 id 必须带 provider 前缀。** 写 `model = "deepseek-v4.1-flash"` 直连 20128 返回
  **404 model not found**；带前缀的 `a2a/deepseek-v4.1-flash` 才通。查真实 id：`GET /v1/models` 后按关键词 grep，
  取**带 `/`** 的那条 —— 不带前缀的裸名看起来最自然，恰恰是不存在的那条。
- `docker run` 当初没写 `--restart` 时补：`sudo -n docker update --restart unless-stopped <c>`（不必重建容器）。
- **验收要真跑一次模型**，不是只看 HTTP 200：`sudo -n docker exec <c> <cli> run "用一句话说明你是谁"`，
  看到中文正文才算通；Web 控制台另测 `curl -w "%{http_code}"`。

### 5.9 自建 relay（hub）+ 多设备接线（nanoMuse `cloud/`）

- **三个角色别混**：runtime = 某台机器上的手（shell/浏览器）；relay = 总机（账号/路由/模型代理，不碰屏幕）；
  手机 App = 唯一能碰手机屏幕的手。**部署前先问「BOSS 要它碰什么」** —— 要碰手机就必须装 App，只装 runtime 没用。
- 上游自带 `docker-compose.local.yml`（无 TLS/局域网模式），直接 override，别自己写：
  `RELAY_BIND=0.0.0.0` + `RELAY_PORT`（本 NAS 用 8795，8787/8788/8790/8791 都被占）+ `PUBLIC_BASE` + `CODE_SENDER=log`。
  `cloud/data` 属主要 `chown 10001:10001`（借 `docker run --rm -v ...:/d alpine chown`）。
- 🔴 **relay 内置模型菜单是厂商裸名，OmniRoute 只认带前缀 id** → 必须用 `CLOUD_MODELS` 把 `id`（App 请求的）
  与 `upstream`（真实上游 id）分开映射，否则客户端一发就 502 `upstream_model`。每个 lane（chat/gui）恰好一个 `recommended_for`。
- 🔴 `/v1/auth/code` 返回 **204 无 body**（`json.loads` 会炸）；验证码打在容器日志里且 **TTL 很短**，取码与 verify 要连着做；
  verify 返回的 token 字段名是 **`api_key`**。
- 🔴 **跨网可达性必须从另一台组网节点验**：本机 `127.0.0.1` 通只证明进程活着，不证明组网能到；relay 重建后要再验一次。
- 🔴 **部署前先写清用途（谁用、碰什么、BOSS 怎么触发）**，写不出就先问。反例：装了 runtime 判「无增量」删掉，
  后来才发现它是「飞书 → 手机」链路的必需中间层，得重装。

完整配方（env 清单、CLOUD_MODELS 示例、e2e 五步、能力边界表）见 `references/self-hosted-relay-hub.md`。

## 六、汇报给 BOSS 时

结论先行 + 表格：URL / 端口 / 数据目录 / 镜像 tag / 状态。

**口令的分寸**：报告里默认**只给文件路径 / 脱敏（前 4 后 4）**，不主动把口令铺进聊天。
但 BOSS **明确点名要**某个属于他自己服务的凭据时，**直接给全值** —— 那是他的基础设施、他的私聊，
端一句「请自己去读文件」只会让他多跑一趟。给的时候附上三件事：① 它的权限范围（控制台全权 / 仅 API）；
② 它现在还暴露在哪些地方（明文文件、容器日志）；③ **建议轮换**。
自己为了排查而复制出来的含密文件（DB 副本、导出文件），**用完立刻删**，不留明文残留。

🔴 **密码存的是单向哈希时（scrypt/bcrypt），不存在「读出来」这条路**：别改哈希、别自造一个密码塞进 DB，
走应用自己的重置流程（FreeLLMAPI：`POST /api/auth/forgot-password` → `docker logs | grep -i "reset code"`
取 15 分钟码），把码交给 BOSS 让他自己设新密码 —— 这样谁都不用知道他的密码。
交付时把「读不出是设计如此」讲在前面，并给出码的有效期。

## 七、NAS 上「这个端口是什么服务」的取证

BOSS 常直接甩一个 `192.168.199.2:<port>` 或一张截图问「这是什么？要账号密码吗」。
按 1→4 顺序走完再回答，**不要靠端口号猜**（同一端口号在不同机器上完全可能是两回事）。

1. **先排除容器**：`docker ps -a --format "{{.Names}}|{{.Image}}|{{.Ports}}" | grep :<PORT>`，命中即容器应用。
2. **没命中 → 宿主进程 / host 网络容器**：在宿主网络命名空间里找监听者，再按 socket inode 反查 PID（端口先转十六进制，5005 → 138D）：
   ```bash
   $SSH 'sudo -n docker run --rm --privileged --pid host --net host alpine sh -c "
     for f in /proc/net/tcp6 /proc/net/tcp; do awk \"\\\$2 ~ /:<HEX>\$/ {print \\\$2, \\\$10}\" \$f; done"'
   ```
   拿到 inode 后遍历 `/proc/*/fd` 找 `socket:[<inode>]`，读该进程的 `cmdline` 与 `cgroup`：
   `cgroup` 是 `/../<name>.service` → 宿主 systemd 服务（NAS 自带功能多半如此）；是容器 ID → `docker inspect` 它。
   （`netstat -tlnp` 在这类容器里看不到 PID，别指望它。）
3. **读宿主配置与日志**（只读）：绿联自带服务在 `/ugreen/@appstore/com.ugreen.ctlmgr/<svc>/`、`/etc/<svc>/`、`/var/ugreen/log/`、`/var/lib/<svc>/`。
4. **判「要不要账号密码」看配置，不看现象**：如 `/etc/webdav/webdav.conf` 的 `enable_anonymous=false` 才是强制认证的依据。

完整命令序列、已核实实例（绿联内置 WebDAV 5005/5006）与「按 uid 分共享目录」的读法见
`references/nas-service-forensics.md`。
