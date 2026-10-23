# 独立 Claude Code 容器配方（NAS / 绿联 DXP4800）

目标：一个**不随任何 agent 容器生命周期消失**的 Claude Code，Web 界面可访问，后端走本机 OmniRoute。

## 一、目录结构

```
/volume2/2-AI/claude-code/      # DY 可写；不要用 /volume1/docker（root drwx------）
├── docker-compose.yml
├── Dockerfile
├── server.js                  # Web 聊天服务器（单文件，无外部依赖）
├── deploy.sh                  # 一键部署，交给 BOSS 只跑这一条
├── .env                       # 600：OMNIROUTE_KEY / CC_TOKEN
├── .cc_token                  # 600：Web 访问口令
├── workspace/                 # 777：CC 工作目录 → /workspace
└── claude-config/             # 777：→ /home/ccuser/.claude
```

挂载目录必须 `chmod 777`（或 chown 到容器内 uid）：容器里是 `ccuser`，宿主目录属主是 `DY`，
bind mount 会覆盖镜像里的目录权限，不放开就是 EACCES。

## 二、Dockerfile

```dockerfile
FROM node:20-bookworm-slim
# 不要 apt-get：Debian 源在国内极慢，是构建卡十几分钟的真凶（不是拉镜像慢）
# 不要只读挂载宿主的 claude 二进制：它会找不到自己的资源目录，工具集被裁剪
RUN npm install -g --allow-scripts=@anthropic-ai/claude-code @anthropic-ai/claude-code@2.1.308
RUN useradd -m -s /bin/bash ccuser
COPY server.js /home/ccuser/server.js
RUN chown ccuser:ccuser /home/ccuser/server.js    # 漏了这行容器内 EACCES
USER ccuser
WORKDIR /workspace
EXPOSE 3000
CMD ["node", "/home/ccuser/server.js"]
```

两条硬约束，各自都有实测代价：

| 写法 | 后果 |
|---|---|
| 只读挂载宿主 `claude.exe` → `/usr/local/bin/claude` | `--version` 正常，但**工具集被裁**：模型说「我没有 Bash 工具」，`which rg git` 全空 |
| `apt-get install git curl procps` | 构建十几分钟卡死；`server.js` 用不到、Claude Code 自带 ripgrep |

`--allow-scripts=@anthropic-ai/claude-code` 不能省：npm 默认拦 postinstall，缺原生组件时
`claude --version` 直接报缺 native module。本地手动补装是 `cd <pkgdir> && node install.cjs`。

## 三、docker-compose.yml

```yaml
services:
  claude-code:
    build: .
    container_name: claude-code-nas
    restart: unless-stopped
    ports:
      - "3111:3000"        # 3000 在 NAS 上被 Gitea 占用
    environment:
      - ANTHROPIC_BASE_URL=http://192.168.199.2:20128   # OmniRoute，原生支持 /v1/messages
      - ANTHROPIC_API_KEY=${OMNIROUTE_KEY}
      - ANTHROPIC_MODEL=openrouter/minimax/minimax-m3.1-flash:free
      - ANTHROPIC_DEFAULT_OPUS_MODEL=a2a/sn-kimi-k3
      - ANTHROPIC_DEFAULT_SONNET_MODEL=openrouter/minimax/minimax-m3.1-flash:free
      - ANTHROPIC_DEFAULT_HAIKU_MODEL=naswb/deepseek-v4.1-flash
      - ANTHROPIC_SMALL_FAST_MODEL=naswb/deepseek-v4.1-flash
      - CLAUDE_CODE_MAX_OUTPUT_TOKENS=32000
      - CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
      - CC_TOKEN=${CC_TOKEN}
      - CLAUDE_BIN=/usr/local/bin/claude
    mem_limit: 1200m
    cpus: 1.5
    volumes:
      - ./workspace:/workspace
      - ./claude-config:/home/ccuser/.claude
    working_dir: /workspace
```

要点：
- 镜像 tag / npm 包版本要 pin，不要 `latest`。
- `mem_limit` + `cpus` 必须给：NAS 可用内存本就紧张。
- 端口先预检（SKILL.md §三），冲突就改并在报告里写明为什么改。
- 三级模型位（DEFAULT / OPUS / HAIKU / SMALL_FAST）都写满：`/model opus` 才有东西可切。

## 四、server.js 必改四处

| # | 上游写法 | 问题 | 改成 |
|---|---|---|---|
| 1 | `exec('claude -p ' + JSON.stringify(msg))` | 命令注入 / RCE | `execFile(CLAUDE_BIN, args)`，参数走数组 |
| 2 | 无鉴权 | 内网任何人可拿 shell | 校验 `CC_TOKEN`，未带返 401 |
| 3 | 模型硬编码 `deepseek-v4-pro` | 换模型要改代码 | 读 `process.env.ANTHROPIC_MODEL` |
| 4 | `cwd: '/workspace'` 写死 | 本地测试无此目录 → ENOENT | `fs.statSync` 探测，不存在回落 `process.cwd()` |

另外必须加 `--dangerously-skip-permissions`（用 `CC_ALLOW_TOOLS=0` 可关）：headless 模式无交互批准，
不加则 Bash/Write 全被权限系统拦，表现是「模型说做完了，文件其实没落地」。

`/health` 返回 `{ok, model, bin, workdir}` —— 排 ENOENT 时这四个字段一次定位。

`execFile` 对 npm 生成的软链可能报 `ENOENT`（本地实测），先 `fs.realpathSync` 解析到真实路径再 spawn 更稳。

## 五、模型：必须按 Claude Code 工具协议实测

**API 层 `tool_use` 通过 ≠ Claude Code 里能用。** 判据只有一条 —— 让模型用 Bash 写文件，**回读文件**。

```bash
docker cp scripts/cc_model_probe.sh <c>:/tmp/cc_model_probe.sh
docker exec <c> bash /tmp/cc_model_probe.sh \
  mac8081/GLM-5.3 openrouter/minimax/minimax-m3.1-flash:free a2a/sn-kimi-k3
```

脚本先跑一个已知可用模型作**对照**：对照也 `NO_TOOL` → 是容器环境问题（资源目录/权限），不是模型问题。
`unrecognized_model` / `Unknown model` 警告对非 Anthropic 模型名是正常的，**别被它带偏去换模型**。

实测矩阵（2026-10，OmniRoute 后端）：

| 模型 id | 智力 | 容器内实测 | 用途 |
|---|---|---|---|
| `vecp/glm-5.2` | 51（付费 ¥9.9） | ✅ 写盘成功 | 对照基线 / 当前最强可用 |
| `a2a/sn-kimi-k3` | 44 | ✅ 约 30s | opus 位 |
| `openrouter/minimax/minimax-m3.1-flash:free` | 42 | ✅ 约 9s | 日常默认 |
| `wbfree/global:deepseek-v4.1-flash` | 40 | ✅ 约 6s | 备用 |
| `naswb/deepseek-v4.1-flash` | 40 | ✅ 约 5s | haiku / small-fast |
| `mac8081/GLM-5.3` / `-thinking` / `Qwen3-Coder` | 45 / 45 / — | ❌ NO_TOOL | **不可用** |

- `auto/*` 别名（`auto/claude-opus` 等）不选最强，会固定落到同一个 flash 模型 —— 显式写模型 id。
- 交付时必须说清「免费池的天花板」：最强可用项与旗舰差多少分，别把免费模型吹成旗舰。

## 六、部署与验收

`deploy.sh`（BOSS 只跑 `sudo bash ~/claude-code/deploy.sh`；能自己跑就别推给他，见 SKILL.md §二.5）：

```bash
set -e; cd "$(dirname "$0")"
docker compose build
docker compose up -d
for i in $(seq 1 40); do curl -sf http://127.0.0.1:3111/health >/dev/null 2>&1 && break; sleep 2; done
curl -s http://127.0.0.1:3111/health; docker compose ps
echo "地址: http://192.168.199.2:3111"; echo "口令: $(cat .cc_token)"
```

验收五件套（缺一不算成功）：

1. `/health` 返回 `{"ok":true,...}`，且 `model` 字段是你要的那个。
2. 不带口令 `curl` → **401**（证明鉴权真的生效，不是摆设）。
3. 带口令真发一轮对话 → 中文正文。
4. **真跑一次工具调用**：让它 `echo web-ok > webtest.txt`，然后用 `read_file` 读 workspace/webtest.txt 回读 ——
   只看模型说「已写入」不算，headless 权限被拦时它照样这么答。
5. `docker exec <c> claude --version` 有版本号；`docker inspect --format '{{.HostConfig.RestartPolicy.Name}}'` = `unless-stopped`。

## 七、上游指南里对本环境有效的坑

| # | 坑 | 处理 |
|---|---|---|
| 3 | 管理用户不在 docker 组 | 全程 `sudo -n /usr/bin/docker`（免密按命令粒度，见 SKILL.md §二.5） |
| 4 | Docker Hub 拉取超时 | UGOS 默认已配 xuanyuan / daocloud / 1panel 三个 mirror，先 `cat /etc/docker/daemon.json` 确认 |
| 5 | Dockerfile 多行粘贴被截断报 `unknown instruction` | 用 write_file + base64 管道传，不要手敲 |
| 9 | 构建十几分钟不动 | **删掉 apt-get 整段**，不是加 `--no-cache`（那是反方向） |
| 10 | server.js 属主 root → EACCES | Dockerfile 里 `chown ccuser` |
| 13 | sudo 需要 TTY | `sudo -n docker ...`（按命令免密） |

改完 Dockerfile 必须**单独重传 + 重 build**：只改 compose 时 `up -d --force-recreate` 换的是容器不是镜像，
build 上下文没变还会命中缓存。判据 `docker exec <c> which claude` 为空 = 镜像里根本没有。

## 八、资源与安全账（交付时要讲）

- 独立容器比「装在现有 agent 容器里」多花 **+400~600MB 内存、+约 630MB 镜像**，换来的是解耦：
  现有 agent 重建/升级不影响它。
- `--dangerously-skip-permissions` 下持有访问口令 = 容器内 shell → **只绑内网、只给强口令**，
  不要做公网端口映射。
- 口令交付：默认给文件路径；BOSS 明确要时给全值，并附权限范围 + 暴露位置 + 建议轮换。
