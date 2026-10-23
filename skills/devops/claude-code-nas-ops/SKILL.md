---
name: claude-code-nas-ops
description: Use when 运维 NAS 上的 claude-code-nas 容器。
---

# Claude Code NAS 容器运维

NAS（DXP4800-【BOSS英文名】 / 192.168.199.2）上独立跑一个 Claude Code 容器，与小卡容器解耦。
部署源：`fubob13013-afk/nas-claude-code`（`docs/deploy-guide.md`，按 DXP4800 写，含 18 条坑），但**必须改造**后才用。

## 现状（已验证可用）

| 项 | 值 |
|---|---|
| 容器 | `claude-code-nas`，restart `unless-stopped` |
| 目录 | NAS `~/claude-code/`（compose + Dockerfile + server.js + .env + .cc_token） |
| 端口 | `3111:3000`（NAS 3000 被 Gitea 占了） |
| Web | `http://192.168.199.2:3111`，首次弹框要口令 |
| 口令 | `~/claude-code/.cc_token`（600） |
| 工作目录 | `~/claude-code/workspace/`，宿主可 SMB 直接看 |
| 后端 | OmniRoute `http://192.168.199.2:20128`（Anthropic `/v1/messages` 原生支持） |
| 版本 | Claude Code 2.1.308 |

## 三种调用方式

1. **Web**：浏览器开 3111，输 `.cc_token`。输入框左侧三态按钮 ⚡自动 / ⚡快 / 🧠深思 可切档（存 localStorage）；`/api/chat` 请求体带 `{"model":"fast"|"deep"|<模型ID>}` 同样生效——**不是只能跑 `ANTHROPIC_MODEL` 那一个模型**。
2. **CLI**（能 `/model` 切档、能交互）：
   `ssh DY@192.168.199.2` → `sudo -n /usr/bin/docker exec -it claude-code-nas claude`
3. **API**（给脚本/其他 agent）：
   `curl -X POST "http://192.168.199.2:3111/api/chat?token=<TOKEN>" -H 'Content-Type: application/json' -d '{"message":"..."}'` → `{"reply":"..."}`

## 模型选型（关键：能聊天 ≠ 能干活）

Claude Code 依赖 Anthropic `tool_use` 协议。**必须在容器内实测**能不能调 Bash，只看 API 层返回 200 会误判。

实测结论：

| 模型 | 工具调用 | 速度 | 说明 |
|---|---|---|---|
| `naswb/deepseek-v4.1-flash` | ✅ | 5s | 默认，不限量 |
| `wbfree/global:deepseek-v4.1-flash` | ✅ | 6s | 不限量，sonnet 位 |
| `a2a/sn-kimi-k3` | ✅ | 30s | 免费池智力最高（44），opus 位，商汤限速 |
| `openrouter/minimax/minimax-m3.1-flash:free` | ✅ | 9s | 会 **429 冷却**，别当默认 |
| `mac8081/GLM-5.3` | ⚠️ 半通 | — | 根因：Claude Code 工具定义 30KB 超 AFS 输入上限被丢弃；网关侧压到 4.6KB 后隔离测试 3/3，但 AFS 上游需重登 GLM 网页会话，未验收，暂不用。**换掉 8081 的选型与部署见技能 `web-model-to-api-gateway`** |

### 双模型自动分流（2026-10-22 上线，已验证）

- 默认 `naswb/deepseek-v4.1-flash`（WB 网关免费、5–6s）→ 日常沟通。
- 疑难自动切 `a2a/glm-5-3`（18s 起）→ 深度推理。
- 判据在 `server.js` 的 `resolveModel()`：消息 >400 字，或命中 `深思|难题|深入|认真想|仔细想|架构|重构|排查|为什么|方案设计|对比分析|性能优化|安全审计|写代码|调试` → deep；请求体 `{"model":"deep"|"fast"}` 可显式覆盖；正文前缀「深思：」强制 deep 且前缀不传给模型。
- 响应带 `model` 字段；Feishu 桥在 deep 时追加 `—🧠 本次 GLM-5.3 深思`；`/health` 同时列 `fast`/`deep`。
- Web 端输入框左侧三态按钮 ⚡自动 / ⚡快 / 🧠深思（存 localStorage）。
- CLI：默认快模型，`/model opus` = GLM-5.3（`ANTHROPIC_DEFAULT_OPUS_MODEL`），`/model sonnet|haiku` = deepseek。
- 实测：显式 fast 6s、显式 deep 18s 且工具真落盘、无 model 字段时关键词命中走 deep 124s（GLM 会自己探容器，慢但答得细）。

当前 compose 配置：默认 `naswb/deepseek-v4.1-flash`，`CC_MODEL_FAST`/`CC_MODEL_DEEP` 显式声明，opus 位 `a2a/glm-5-3`，sonnet 位 `wbfree/global:deepseek-v4.1-flash`，haiku 位 `naswb/deepseek-v4.1-flash`。

实测命令（容器内，判定依据是文件真落盘）：
```bash
sudo -n /usr/bin/docker exec claude-code-nas rm -f /workspace/t.txt
sudo -n /usr/bin/docker exec claude-code-nas /usr/local/bin/claude -p \
  'Use the Bash tool to run: echo OK > /workspace/t.txt   Then reply only: done' \
  --model <MODEL> --dangerously-skip-permissions
sudo -n /usr/bin/docker exec claude-code-nas cat /workspace/t.txt   # =OK 才算通
```

## 附件上传（2026-10-22 上线，已验）

- Web 端输入框旁 📎 按钮，或直接在输入框里 **粘贴截图**（监听 paste 事件自动上传）。上限 50MB。
- 上传接口 `POST /api/upload?name=<文件名>`，body 是裸二进制（不走 multipart，Node 无需第三方依赖），需带 `x-cc-token` 或 `?token=`。
- 文件落 `/workspace/uploads/<时间戳>-<安全名>`（宿主机 `~/claude-code/workspace/uploads/`，SMB 可见）；前端自动把绝对路径填进输入框，模型用 Read 工具读。
- 实测：txt 读出「蓝色猎鹰-42 / 2026-11-01」；PNG 读出「ZEBRA-8899」——图片 OCR 也能走通（靠模型自身多模态，不需额外 OCR）。
- 也可绕过 UI：把文件拖进 `~/claude-code/workspace/`（SMB），然后告诉 Claude 路径即可。

## 坑（都踩过）

- **不要挂载单个 `claude.exe`**：二进制找不到自己的资源目录，工具集被裁剪（模型会回“我只有 open_url 工具”）。必须在镜像内 `npm install -g`。
- **Dockerfile 必须自检**：`npm install -g ... && /usr/local/bin/claude --version` + `RUN test -x /usr/local/bin/claude`。曾产出 304MB 残镜像（装了一半、无 claude），容器起来后 `spawn /usr/local/bin/claude ENOENT`。
- **`docker compose up --force-recreate` 可能重建成残镜像**：改了 compose 只想重启时加 `--no-build`，否则先确认镜像内 claude 还在。
- **别装 apt**：`apt-get install git curl` 在国内会挂十几分钟；server.js 只用内置模块，claude 自带 ripgrep。
- **`execFile` 不能 spawn npm 生成的 symlink**（报 ENOENT），要指向真实可执行文件；本项目直接 npm 装，`/usr/local/bin/claude` 可执行。
- **`unrecognized_model` 警告是无害的**（只是假设 200k 上下文），不影响工具调用；工具失效要查模型协议和二进制，不是这条警告。
- **headless 必须 `--dangerously-skip-permissions`**，否则 Bash/Write 全被拦；代价是拿到 CC_TOKEN = 容器内 shell，所以只开内网。
- **`DY` 有 NOPASSWD `/usr/bin/docker`**：可以自己 build/up/logs，不用 BOSS 输密码。
- **上游 server.js 有 `exec` 拼接 RCE**：已改 `execFile` + `CC_TOKEN` 401 鉴权。

- **slim 镜像里没有 `curl`**：从容器内验证 HTTP 连通性时 `docker exec ... curl` 会 `not found`。写个 12 行 node 脚本 `docker cp` 进去跑（`http.request` + `process.env`），别为了测一次去 apt 装 curl（国内会挂）。
- **改 `server.js` 必须 rebuild**：它被 `COPY` 进镜像，`docker cp` 覆盖运行中容器的 `/home/ccuser/server.js` 实测会导致文件缺失 → 容器 crash loop（`ENOENT /home/ccuser/server.js`）。正确做法 `docker compose up -d --build`（COPY 层缓存，几十秒）。
- **第二个容器要接进同一个 compose 网络**：compose 项目网络名是 `<目录名>_default`（本项目 `claude-code_default`）。桥接类容器用 `networks: {claude-net: {external: true, name: claude-code_default}}` 接入，之后 `http://claude-code-nas:3000` 直接用容器名当 DNS。

## 飞书入口（爱因斯坦-Claude）

容器 `claude-feishu-bridge` 把飞书长连接接到本容器的 `/api/chat`，BOSS 在飞书直接跟它说话。
完整搭建与排障见 `references/feishu-bridge.md`。

| 项 | 值 |
|---|---|
| 飞书应用 | `爱因斯坦-CLaude`（BOSS 在开放平台建，凭证只存 NAS `~/claude-feishu/.env` 600） |
| 桥容器 | `claude-feishu-bridge`，目录 NAS `~/claude-feishu/` |
| 连接方式 | 长连接 WebSocket（NAS 无公网 IP，不能用 webhook 回调） |
| 行为 | 私聊直接回；群里**必须 @** 才理；先回「收到」再回结果 |
| 边界 | 只能碰 `~/claude-code/workspace`（容器只挂 workspace + claude-config） |

改了桥代码：`cd ~/claude-feishu && sudo -n /usr/bin/docker compose build && up -d`；看日志 `sudo -n /usr/bin/docker logs --tail=40 claude-feishu-bridge`。

## 常用命令

```bash
# 改模型后生效（不重建镜像）
cd ~/claude-code && sudo -n /usr/bin/docker compose up -d --force-recreate --no-build
# 健康检查
curl -s http://127.0.0.1:3111/health
# 看日志
sudo -n /usr/bin/docker logs --tail=40 claude-code-nas
# 真正重建（改了 Dockerfile/server.js）
cd ~/claude-code && sudo -n /usr/bin/docker compose build --no-cache
```

## 传文件到 NAS

scp/sftp 被限，用 base64 管道：
```bash
B64=$(base64 -w0 本地文件)
ssh -i /opt/data/.ssh/id_ed25519 DY@192.168.199.2 "echo '$B64' | base64 -d > 目标路径"
```
整目录用 `tar czf - dir | base64` + 远端 `tar xzf - --strip-components=1`。
