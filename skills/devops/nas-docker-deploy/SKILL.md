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
curl -s http://192.168.199.2:<hostport>/<health-path>    # 从容器内也要能访问（证明 LAN 通）
```

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

`ghcr.io/caigee-cmd/cli2api:latest`，端口 3010，数据 `/volume2/2-AI/cli2api/data`（**不是**规格里给的 `/volume1/docker/...`）。

- **管理员 key 是启动时自动生成、直接打进容器日志的**（`sudo -n docker logs cli2api | head`）→ 局域网内谁都能读到日志，交付时必须提醒 BOSS 首次登录就改掉。
- **新容器一律加 `--memory <上限>`**：NAS 可用内存本就紧张（实测余 8G 左右，同时跑着 OmniRoute / Emby / MoviePilot 等），无上限的新容器可能把整机拖垮。

## 六、汇报给 BOSS 时

结论先行 + 表格：URL / 端口 / 数据目录 / 镜像 tag / 状态。凡涉及口令，只给**文件路径**，绝不把口令贴进聊天。
