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

## 二、两个必踩的坑

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

## 三、部署前预检

```bash
$SSH DY@192.168.199.2 'sudo -n docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'   # 已占用容器
$SSH DY@192.168.199.2 'sudo -n docker ps --format "{{.Ports}}" | tr "," "\n" | grep <PORT>' # 端口冲突
$SSH DY@192.168.199.2 'sudo -n docker info | grep -E "Docker Root Dir|Registry Mirrors"'      # 镜像存 /volume1/@docker
$SSH DY@192.168.199.2 'df -h /volume2 | tail -1'
```

镜像源：NAS 配的 mirror（xuanyuan / daocloud / 1panel）**只覆盖 docker.io**。ghcr.io 直连可用且不慢（678MB 镜像 76s）。国内镜像仓备选 `ghcr.nju.edu.cn/<org>/<repo>:<tag>`。

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
- 完成向导前 8088 无鉴权开放（`setup_required=true`），账号由 BOSS 自己在页面建。

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

## 六、汇报给 BOSS 时

结论先行 + 表格：URL / 端口 / 数据目录 / 镜像 tag / 状态。

**口令的分寸**：报告里默认**只给文件路径 / 脱敏（前 4 后 4）**，不主动把口令铺进聊天。
但 BOSS **明确点名要**某个属于他自己服务的凭据时，**直接给全值** —— 那是他的基础设施、他的私聊，
端一句「请自己去读文件」只会让他多跑一趟。给的时候附上三件事：① 它的权限范围（控制台全权 / 仅 API）；
② 它现在还暴露在哪些地方（明文文件、容器日志）；③ **建议轮换**。
自己为了排查而复制出来的含密文件（DB 副本、导出文件），**用完立刻删**，不留明文残留。

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
