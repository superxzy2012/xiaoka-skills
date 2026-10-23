# 网页端模型转 API：项目选型表

按「能不能直接覆盖目标平台 + 是否可容器化 + 维护活跃度」排序。星数与活跃度会变，用前先 `gh api repos/<owner>/<repo>` 看 `pushed_at`。

## 第一梯队

### router-for-me/CLIProxyAPI
- 覆盖：OpenAI（Codex OAuth）、Claude、Gemini（Antigravity / AI Studio / Vertex / Gemini CLI）、Grok（xAI）、Kimi、Meta Muse、Devin
- 登录：OAuth 账号授权，凭证落 `auths/` 卷
- 部署：官方镜像 `eceasy/cli-proxy-api:latest`，仓库自带 `docker-compose.yml`
- 协议：OpenAI（含 Responses）、Claude、Gemini 三种入口
- 登录 CLI 参数：`-codex-login` / `-codex-device-login` / `-claude-login` / `-antigravity-login` / `-kimi-login` / `-kimi-ai-login` / `-meta-login` / `-devin-login`，通用 `-no-browser`、`-oauth-callback-port`
- 配套面板：`router-for-me/Cli-Proxy-API-Management-Center`（Vite SPA，无官方镜像）
- 注意：它是「客户端/CLI 账号」路线，不是网页 Cookie 路线；挂的是订阅额度。

### xiaoY233/Chat2API
- 覆盖：DeepSeek、GLM、Kimi、MiniMax、Qwen（含 qwen-ai）、Z.ai、Perplexity、Mimo
- 登录：网页 Cookie / OAuth，界面里逐平台添加
- 形态：Electron 33 + React + TS 桌面应用，内嵌 Koa 服务，默认 `8080`，暴露 `/v1/chat/completions`、`/v1/models`，支持 API key 鉴权
- 能力：function calling 走提示词工程实现（跨模型通用）、上下文滑动窗口、模型映射、仪表盘
- 许可证：GPL-3.0
- 容器化要点：无官方 Docker；跑在 NAS 上必须 Xvfb + noVNC，让 BOSS 在浏览器里点登录。
- 发行包：releases 直接提供 `Chat2API-<ver>-x86_64.AppImage`（约 107MB），**不要自己 build**；容器内用 `--appimage-extract` 解包再跑（无 FUSE）。

## 第二梯队（单平台兜底）

| 项目 | 覆盖 | 登录 | 备注 |
|---|---|---|---|
| `HanaokaYuzu/Gemini-API` | Gemini 网页版 | Cookie（`__Secure-1PSID` 系） | Python 库，非服务 |
| `izaart95-jpg/GLM-Free-API` | chat.z.ai | LocalStorage `token` → `ZAI_TOKEN` | MIT，Go，带 token 池 |
| `xiaoY233/GLM-Free-API` | 智谱清言 | `chatglm_refresh_token` | GPL-3.0，有 Dockerfile，2026-02 后基本停更 |
| `realasfngl/Grok-Api` | Grok | 账号/Cookie | 小项目，稳定性看上游 |
| `lanqian528/chat2api` | ChatGPT 网页 | Access Token | 经典项目，Cloudflare 与网页改版影响大 |

## 不推荐

- `xtekky/gpt4free`：星最多，但走爬虫/逆向聚合而非账号登录态，接口漂移频繁，不适合当生产网关。
- 各家 `*-free-api` 的旧分叉：多数 2024–2025 停更，Cookie 字段名早已变。

## 判断项目是否值得接

1. `pushed_at` 在近 30 天内。
2. README 明确写了 **function calling / tool_use 支持**（没有这行基本等于只能聊天）。
3. 有官方 Docker 镜像或 Dockerfile（否则容器化成本翻倍）。
4. 登录态是「一次性登录后落盘可刷新」，不是每次请求带浏览器 Cookie 字符串。
5. 许可证允许自用；GPL/AGPL 不要嵌进对外分发的产品。
