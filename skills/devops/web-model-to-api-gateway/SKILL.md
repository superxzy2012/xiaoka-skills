---
name: web-model-to-api-gateway
description: Use when 把网页端模型账号转成 OpenAI 兼容 API。
version: 1.0.0
author: 小卡
license: MIT
metadata:
  hermes:
    tags: [gateway, reverse-proxy, docker, oauth, nas]
    related_skills: [claude-code-nas-ops, chat2api-gateway-doctor, omniroute-gateway-ops]
---

# 网页端模型 → API 网关

## When to Use

- BOSS 要把 ChatGPT / Claude / Gemini / Grok / DeepSeek / GLM / Kimi / MiniMax 的网页或客户端账号转成 API。
- 要评估、替换或重做 8081 这类自建 web→API 网关。
- 要在 NAS 上 Docker 化一个「浏览器登录一次、容器拿登录态」的模型代理。

## 铁律：先查上游，别逆向

自建网关（如 Mac 8081 的 AFS+Flask）本质是「Electron/浏览器壳 + 本地 OpenAI 桥」。这类东西 GitHub 上已有产品化实现（选型表见 `references/project-landscape.md`），逆向自己的旧方案等于重做一个更差的版本。

**先认脸，再决策**：自建壳子多半是开源项目改名。实测 Mac 的 `AFS.app` 就是 **Chat2API 1.6.0**——`CFBundleIdentifier = com.chat2api.manager`，userData 在 `~/Library/Application Support/chat2api`，asar 内 `toolCalling` 命中 96 次。改名不换 bundle id，一条命令就能定源：

```bash
defaults read /Applications/<X>.app/Contents/Info.plist | grep -E "CFBundleName|Identifier|ShortVersion"
# asar 特征词计数（容器里没有 strings 时用 python 读字节）
python3 -c "import re;d=open('/Applications/<X>.app/Contents/Resources/app.asar','rb').read();print({k:len(re.findall(k.encode(),d)) for k in ['chat2api','toolCalling']})"
```

同源意味着三件事，直接影响方案选择：登录态格式 1:1 兼容（可跨机搬，见 `references/login-state-transplant.md`）、新版本内核可以直接搬进旧容器、上游故障两边同步（Mac 报 500 时容器里必然也不通，别再花时间证明「另一台是不是好的」）。

决策顺序：

1. 现成项目能覆盖目标平台 → 直接用，接到已有聚合层后面。
2. 只差个别平台 → 现成项目 + 单平台容器补齐。
3. 全都不行（罕见）→ 才考虑逆向；动手前先确认上游只是登录态失效，不是架构问题。

## 架构：三层，别混

| 层 | 职责 | 本机选型 |
|---|---|---|
| 聚合层 | 统一出口、按模型名路由、额度与降级 | OmniRoute（NAS `:20128`，已有） |
| 转换层 | 各家网页/客户端账号 → OpenAI/Claude 协议 | CLIProxyAPI（OAuth 类）+ Chat2API（网页 Cookie 类） |
| 登录态 | 浏览器登录一次，凭证落盘 | OAuth 写 `auths/` 卷；Cookie 写容器卷 |

聚合层已经存在时**不要新建**（别为这件事再装 new-api / one-api）：把转换层注册成 provider 即可。

## 平台分工

- **OAuth 系**（ChatGPT/Codex、Claude、Gemini/Antigravity、Grok、Kimi、Meta）→ CLIProxyAPI。
- **网页 Cookie 系**（DeepSeek、GLM、Kimi、MiniMax、Qwen、Z.ai、Perplexity）→ xiaoY233/Chat2API（Electron 桌面版，需 Xvfb 容器化）。
- 两边都支持的（Kimi）优先走 OAuth，Cookie 会随网页改版失效。

## 部署 CLIProxyAPI（NAS，已验证）

```bash
sudo -n /usr/bin/docker pull eceasy/cli-proxy-api:latest   # 198MB
# 目录：~/cli-proxy/{config.yaml,docker-compose.yml,auths/,logs/}
```

`config.yaml` 最小可用（`config-version` 必填，否则按旧 schema 解析）：

```yaml
config-version: 8
server:
  port: 8317
  host: ""
management:
  allow-remote: true
  secret-key: "<随机16字节>"
access:
  api-keys:
    - "sk-cpa-<随机>"
```

compose 只映射 `8317:8317` 就够跑 API；官方还给了 8085/1455/54545/51121/11451，那是各平台 OAuth 回调口，只有走「本机回调」路线时才需要。挂 `./auths:/root/.cli-proxy-api` 和 `./logs:/CLIProxyAPI/logs`，`restart: unless-stopped`。

改 config 不用重启：容器内有 file watcher，日志会打 `configuration updated`。

### 出网必须走代理（大陆环境）

OpenAI / Anthropic / Google 对大陆出口 IP 直接拒：`-codex-device-login` 会报 `403 unsupported_country_region_territory`，看着像账号问题，其实是出口 IP 问题。先配代理再登录：

```yaml
requests:
  proxy-url: "http://<NAS局域网IP>:7891"
```

`requests.proxy-url` 是启动期读取的，改完要 `docker restart cli-proxy-api`。容器内 `127.0.0.1` 是容器自己，指向宿主机代理必须写 NAS 的局域网 IP。

同一个代理也用于下载：NAS 直连 GitHub release 会超时（curl exit 28），要加 `--proxy http://127.0.0.1:7891`（在 NAS 宿主机上执行时用回环地址，在容器里用局域网 IP）。

## 登录态获取（最大的坑）

OAuth 的 redirect_uri 是 `http://localhost:<port>`，**浏览器在哪台机器，回调就落在哪台机器的 localhost**。容器在 NAS、浏览器在 BOSS 的 Mac → 回调打不到容器，登录必然失败。三条可行路径，按优先级：

1. **设备码流程**：`-codex-device-login`，无回调，任何机器都能完成。首选。设备码有时效（约 15 分钟），BOSS 不在线时别提前生成，等他回话再跑；过期就重跑一遍拿新码。
2. **在有浏览器的机器上跑登录**：Mac 有 SSH 通道时，在 Mac 上执行 `-claude-login -no-browser`，把打印的 URL 给 BOSS 点，回调落 Mac 的 localhost，再把生成的 auth json 拷进 NAS `auths/`。BOSS 只需点链接，不用自己敲命令。
3. **SSH 端口转发**：BOSS 机器上 `ssh -L <port>:127.0.0.1:<port>` 把回调口转给容器。

不要试图把容器端口映射成回调地址——redirect_uri 由上游写死，映射无效。

### 复用已有机器上的登录态（跨机搬迁，已验证）

BOSS 已经在 Mac/Windows 上登过一次时，**不要让他逐个账号重登**。Chromium 系 cookie 是「明文 `value` + 密文 `encrypted_value`」混存，refresh token / JWT 通常是明文，直接读出来到目标端「供应商 → 手动输入凭证」重新换发会话即可。**不要碰 macOS 钥匙串，也不要搬 `Cookies` 文件本体**（换机后会话要重新换发，且指纹类 cookie 搬过去更容易被风控）。

完整配方（只读 sqlite 命令、各厂商 token 落点表、UI 注入代码、失效判据、跨平台换 app.asar 升级内核）见 `references/login-state-transplant.md`；批量列 cookie 用 `scripts/dump_electron_cookies.py`。

三条最容易踩的判断错误：

- **403 不等于 cookie 过期**：上游按**服务端出口 IP 的国家**做准入，令牌搬到另一地区/另一出口的机器上照样 403。判据是先确认令牌结构完好（长度、能否换发），再实测服务端出口国家；两者都对才去怀疑账号。别反复重搬 cookie —— 换出口比换 cookie 便宜得多。这条对 Cookie 系与 OAuth 系都成立（OAuth 侧表现为 `403 unsupported_country_region_territory`）。

- **「cookie 全加密所以搬不了」是错的**：先量 `length(value)`，`>40` 且形如 JWT/refresh token 就是明文可直取。
- **「验证成功 / 账户在线」≠ 能出话**：加完必须发一条真实 chat 请求，检查 `content` 非空。上游返回 200 但正文空，是网页端签名/指纹校验把请求挡了，令牌本身有效——此时别再重搬，改去查上游协议。

## 验证

- 无 key 请求 `/v1/models` 应得 **401**（鉴权正常，不是故障）。
- 带 key 返回 `{"data":[],"object":"list"}` = 服务活着但**还没挂账号**。
- 挂上账号后 `/v1/models` 要出现真实模型；再用一条带 `tools` 定义的请求确认 **tool_use 透传**——web 转 API 的通病就是工具调用丢失，只测聊天会误判成功。
- **但别据此断言「这个项目不支持工具调用」**：Chat2API 1.4.0 有完整 `src/main/proxy/toolCalling/`（toolParser / toolFormatConverter / streamToolHandler / providerProfiles），界面也有「工具调用」入口。只 grep `server.ts` 会得到完全相反的结论（server.ts 只做纯转发，工具在子系统里）。

## 坑

- **二进制名是大写** `/CLIProxyAPI/CLIProxyAPI`，`which` 和 `ls /usr/local/bin` 都找不到；查 `docker top <容器>` 的 CMD 才准。
- **健康检查是 `/healthz`**，`/health` 返回 404，别据此判定服务挂了。
- **没有内置管理面板**：`/management.html`、`/management` 都是 404；管理接口在 `/v0/management/*`（要 secret-key 头）。面板是独立仓库 `router-for-me/Cli-Proxy-API-Management-Center`（Vite SPA，需自行 build 后 nginx 托管）。
- **免费额度 ≠ 不限量**：OAuth 挂的是订阅账号额度，不能当「不限量」通道写进默认模型；不限量要留给本地上游通道。
- **Electron 类项目（Chat2API）不能直接跑在无头容器**：需要 Xvfb + noVNC 才能让 BOSS 在浏览器里完成网页登录；纯 CLI 容器化会卡在「没有界面可登录」。配方见下节。
- **别用单个文件 grep 断言产品能力**：`server.ts` 里 `tools|tool_calls` 零命中 ≠ 不支持工具调用。先 `gh api repos/<o>/<r>/git/trees/HEAD?recursive=1` 列目录，看有没有 `toolCalling/`、`adapters/prompt/` 这类子系统，最后才读实现。误判会让整条正确路线被否掉。
- **许可证**：Chat2API 是 GPL-3.0，自用无碍，对外分发要注意；CLIProxyAPI 商用前先看 `commercial-mode` 配置项。
- **重启后 Xvfb 起不来 → Electron 报 `Missing X server or $DISPLAY` + 容器无限重启**：上一轮留下的 `/tmp/.X99-lock`、`/tmp/.X11-unix/X99` 没清，Xvfb 直接退出。把 `rm -f /tmp/.X99-lock /tmp/.X11-unix/X99` 写在 start.sh 第一行。症状极易误判成「新内核不兼容」，换 asar 前先确认 X 起得来。
- **socat 中继不持久**：`docker exec -d` 手工起的 socat 一重启就没了（CDP 9322、API 8081 同时挂）。两条中继都要写进 start.sh（`9223→9222`、`8081→8080`），别只留一条。
- **`docker cp` 保留源文件权限**：把 644 的脚本 cp 进去当 entrypoint，容器起不来（`permission denied`）。宿主机先 `chmod 755` 再 cp；容器已停时无法 `docker exec chmod`，只能从宿主机侧修。
- **对话框遮罩拦截点击**：向导/弹窗打开时点背后的导航按钮会被遮罩吃掉，Playwright 报 actionability 失败。对话框内的按钮统一 `el.evaluate("e => e.click()")`；文本输入优先 `el.evaluate("e => e.focus()")` + `pg.keyboard.insert_text(v)`（`fill()` 对这类受控输入常静默不生效，无报错）。
- **通用 `/tmp/<script>.py` 会撞权限**：`ssh ... "echo '<b64>' | base64 -d > /tmp/x.py"` 撞上别的用户留下的同名文件会 `Permission denied`。每次用带用途的唯一文件名。

## Chat2API 容器化（Electron + noVNC）

用官方 Linux 包，别自己 build（源码 build 要下 Electron + electron-builder，慢且常缺库）：

1. releases 取 `Chat2API-<ver>-x86_64.AppImage`（约 107MB），NAS 上下载要带代理。
2. Dockerfile：`debian:bookworm-slim` + `xvfb x11vnc novnc websockify` + Electron 运行库（`libgtk-3-0 libnss3 libasound2 libgbm1 libxss1 libxtst6 libxrandr2 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libpango-1.0-0 libcairo2 libx11-xcb1 fonts-noto-cjk`）。
3. 容器里没有 FUSE，AppImage 不能直接执行：`./app.AppImage --appimage-extract` 解出 `squashfs-root`（重命名为 `electron`）再跑。
4. **不要 `exec AppRun --no-sandbox`**：AppRun 会拿 `$1` 当可执行名沿父目录向上找，参数是 flag 时找不到 → `APPDIR` 解析成 `/`，报 `/chat2api: No such file or directory`（容器反复重启但 noVNC 照常 200，极易误判成「起来了」）。正确做法：`export APPDIR=/app/electron` 后直接 `exec /app/electron/chat2api --no-sandbox --disable-gpu --disable-dev-shm-usage`，并设 `ELECTRON_DISABLE_SANDBOX=1`（root 身份不加起不来）。
5. 启动顺序：`Xvfb :99` → `x11vnc -display :99 -forever -shared -nopw -rfbport 5900` → `websockify --web=/usr/share/novnc 6080 127.0.0.1:5900` → `socat` 桥（见下）→ exec Electron。现成文件见 `templates/chat2api-Dockerfile` 与 `templates/chat2api-start.sh`。
6. 端口分工：`8080` 是它输出的 OpenAI 兼容 API（`/v1/chat/completions`、`/v1/models`，可开 API key），`6080` 是 noVNC 操作界面；数据落 `/root/.config`（`~/.config/chat2api/`），挂卷持久化，重建容器不丢登录态。代理**不会自动启动**，要在界面点「启动代理」。
7. 验收顺序：noVNC 出画面 → 界面里登录一个平台 → 宿主机 `curl :8080/v1/models` 出现模型 → 再发一条带 `tools` 的请求。**首启时 8080 不监听是正常的**：`~/.config/chat2api/` 只有 Electron 自己的 `Cookies`/`Cache`、没有 `config.json`，说明它还停在配置向导页，不是崩溃；先让 BOSS 在 noVNC 里登录并走完向导，端口才开。

### 代理只绑容器内 127.0.0.1（必踩）

「代理设置 → 基础配置 → 绑定地址」默认 `127.0.0.1`，此时 docker 端口映射 `<宿主>:8080` 打不通（宿主 curl 000），容器间也打不通。两条解法，按可靠度：

1. **socat 桥 + 共享网络（推荐，已验证）**：容器内 `socat TCP-LISTEN:8081,fork,reuseaddr TCP:127.0.0.1:8080 &`；再 `docker network create c2a-net` + `docker network connect c2a-net chat2api` + `docker network connect c2a-net <调用方>`，调用方直接用 `http://chat2api:8081/v1`。不改应用配置、不重建容器、不丢登录态。
2. 在界面把绑定地址改成 `0.0.0.0` 保存。⚠️ 用脚本改 React 受控输入**看着改了、保存不生效**（刷新后回退成 127.0.0.1）；真要改必须真人点，且改完「停止代理 → 启动代理」后 `docker exec <c> netstat -lnt | grep 8080` 确认监听地址真的变了。

`/v1/models` 返回模型列表**不代表能用**：0 账号时列表来自内置 model-mapping，实际请求必失败。判据是「供应商页在线账号数 > 0」。

### 版本升级：跨平台换 app.asar（已验证）

Mac/Windows 版内核常比 Linux release 新（实测 AFS 1.6.0 vs release 1.4.0，1.4.0 只认 `GLM-5.1`，1.6.0 出 `GLM-5.3`）。Electron 的 `app.asar` 是纯 JS 包，可以直接搬进容器覆盖：

```bash
# 宿主侧备份 → 拷入 → 容器内再留一份旧版 → 重启
docker cp <c>:/app/electron/resources/app.asar ./app.asar.orig
docker cp ./app.asar.new <c>:/app/electron/resources/app.asar.new
docker exec <c> sh -c "cp /app/electron/resources/app.asar /app/electron/resources/app.asar.old && mv /app/electron/resources/app.asar.new /app/electron/resources/app.asar"
docker restart <c>
```

前置检查：asar 里有 `.node` 原生模块就**不能**跨平台换（ABI 不匹配，起不来）。先解析 asar header 统计 `.node` 与 `unpacked` 数量，全 JS 才动手。升级后模型列表会立刻变，但**已加账号与令牌不受影响**（在 userData 里，不在 asar 里）。

### 给 Claude Code 用：Anthropic 适配层

Chat2API 只出 OpenAI 协议，Claude Code 只吃 `/v1/messages`。中间加一层薄适配容器（`c2atools`，宿主 `8321`）即可，两种协议实测都能正确产出 `tool_calls` / `tool_use`。转换映射与实现要点见 `references/anthropic-adapter.md`。

### 用 CDP 驱动这个 Electron（可选但强烈建议）

想脚本化点界面、或远程确认向导页状态，加 `--remote-debugging-port=9222`。两个坑：

- **DevTools 只绑容器内 `127.0.0.1`**，`--remote-debugging-address=0.0.0.0` 对 Electron 无效，docker 端口映射也够不到（宿主机 curl 得 000/connection refused）。解法：容器内跑 `socat TCP-LISTEN:9223,fork,reuseaddr TCP:127.0.0.1:9222 &`，映射 `<宿主端口>:9223`。
- **宿主 9222 已被抖音 headless Chrome 占用**，映射要用 9322 之类；冲突时报 `port is already allocated`。

然后 `curl http://<NAS>:9322/json/list` 拿 page 的 `webSocketDebuggerUrl`，用 Playwright `connect_over_cdp` 接管。

驱动这个 React 界面时的三个坑（都实测踩过）：

- `input[type=number]` 不能 `fill()` 文本（报 `Cannot type text into input[type=number]`）；按 `value` 或 `placeholder` 定位目标输入框，别用索引（页面里 input 顺序会变）。
- 受控组件要用原生 setter 再派发事件，否则 React state 不更新：
  ```js
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set;
  setter.call(el, '0.0.0.0');
  el.dispatchEvent(new Event('input',{bubbles:true}));
  el.dispatchEvent(new Event('change',{bubbles:true}));
  ```
- 按钮文案会随状态变（「启动代理」↔「停止代理」），且分散在不同 tab（状态监控 / 基础配置）；每次操作前先 `document.body.innerText` 确认当前页在哪个 tab、按钮叫什么。

### 构建：apt 走代理会慢到怀疑人生

`docker build` 里 `apt-get install` 这些 Electron 运行库，经大陆代理能跑 20 分钟以上（`Get:` 行一条条几百 KB）。所以：**构建一律放后台**（`background=true, notify=true`），别用前台等——前台 420s 超时会让人以为卡死。

**别装 `fonts-noto-cjk`**：单包 56MB，经代理能卡住 30 分钟不前进（日志停在最后一行不动）。换 `fonts-wqy-microhei`（约 5MB）就够中文显示。卡住的构建在 NAS 上**杀不掉**——`sudo -n pkill` 会报 `a password is required`（只有白名单命令能免密 sudo），所以一开始就别引入大包。

构建「成功」不等于新层生效：`docker compose up -d --build` 偶发沿用旧镜像（容器内 `which socat` 为空但 Dockerfile 里明明有）。判据只看容器内实际情况（`docker exec <c> which <pkg>`、`cat /app/start.sh`），不符就单独 `docker build -t <tag> .` 再 `up -d --force-recreate`。临时补包可以直接 `docker exec <c> apt-get install -y <pkg>` + `docker restart`（重建容器才会丢）。

> 状态：noVNC `:6080`、CDP `:9322`、容器内 API `8081` 均通；内核已换到 1.6.0（模型列表出 `GLM-5.3`）。GLM / MiniMax 令牌搬迁成功、账户在线，但真实对话仍失败（GLM 返回 200 空正文、MiniMax 401）——上游网页端签名/指纹校验，属协议层问题，不是搬运或部署问题。

## 单平台兜底

当统一项目缺某个平台时，用单平台 `*-free-api`（Node/Python + Dockerfile，Cookie 粘贴）补齐，别为此改主项目代码。清单与覆盖情况见 `references/project-landscape.md`。
