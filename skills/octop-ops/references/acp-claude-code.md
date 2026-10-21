# Claude Code ACP × OmniRoute 免费模型

零成本给 Octop 专家装上「完整编程 agent」：Claude Code 前端 + 免费模型后端。

## 链路

```
Octop agent ── ACP (stdio JSON-RPC) ──> claude-agent-acp ── Anthropic /v1/messages ──> OmniRoute 20128 ──> 免费模型
```

`initialize` 回 `authMethods: []`：不预置任何登录，认证全靠环境变量。

## 它只读这三个 env

| 变量 | 作用 |
|---|---|
| `ANTHROPIC_AUTH_TOKEN` | 网关 key |
| `ANTHROPIC_BASE_URL` | 网关根地址（**不要带 `/v1`**，客户端自己拼） |
| `ANTHROPIC_CUSTOM_HEADERS` | 额外头，一般不用 |

不认 `ANTHROPIC_API_KEY`，也不认 `ANTHROPIC_MODEL`——模型只认 `settings.json`。

## 全局 runner 配置

`GET /api/acp` → 改 `runners.claude_code` → `PUT /api/acp`：

```json
{
  "enabled": true,
  "trusted": true,
  "command": "npx",
  "args": ["-y", "@zed-industries/claude-agent-acp"],
  "env": {
    "ANTHROPIC_BASE_URL": "http://192.168.199.2:20128",
    "ANTHROPIC_AUTH_TOKEN": "<OmniRoute key>",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1",
    "DISABLE_AUTOUPDATER": "1",
    "HOME": "/data",
    "PATH": "/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
  }
}
```

`HOME=/data` 决定 settings.json 落点 → `/data/.claude/settings.json`（`{"model": "<model id>"}`）。

## 每 agent 启用

`GET /api/agents/{aid}/acp` → 改 `tool_enabled=true` + 同一份 `runners.claude_code` → `PUT /api/agents/{aid}/acp`。全局配置不会下发给 agent。

## 模型选择（实测口径）

| 模型 | 首包 | 一个「写文件」任务 | 备注 |
|---|---|---|---|
| `openrouter/minimax/minimax-m3.1-flash:free` | ~2s | ~30s 完成 | 日常首选 |
| `openrouter/nvidia/nemotron-3-ultra-550b-a55b:free` | 慢 | 300s 未完成 | 智力最强，留给难题 |
| `oc/north-mini-code-free` | — | — | 429 冷却，代码专用但限流 |

选型前必须探 `tool_use`：给 `/v1/messages` 带 `tools` 发一问，回包 `content` 里有 `tool_use` block 才算能用——「列表里有」不等于「能调工具」。

## 自建 stdio 客户端最小流程

`initialize` → `session/new` → `session/prompt`，循环处理回来的 `session/update`：

- `agent_message_chunk` → 正文
- `agent_thought_chunk` → 思考，丢弃
- `available_commands_update` → 噪声，丢弃
- `session/request_permission` → **收到就回 allow**，否则工具调用挂到超时

自己设硬超时（如 `ACP_TIMEOUT=200`），子进程挂住不会自己退。

## 判别 ACP 是否真被调用

Octop agent 自带 `execute` 工具，让它「写个文件」它会优先走 execute（快、稳），**成功不代表 ACP 生效**。要确认只有两条路：

1. 直连 `claude-agent-acp` 跑自建客户端（最干净）；
2. 查网关调用日志 `/app/data/call_logs/<日期>/` 里有没有对应模型的 `messages` 请求。
