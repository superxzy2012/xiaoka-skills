# MCP token 签发（hive: obsidian / skillbox）

任务形状：`inbox/task_*.json` 写着「为 <agent> 签发 MCP token（nonce: FR-MCP-XXXXXX）」，要求落
`~/A2A/secrets/mcp-token-<id>.md` 并写 receipt。交付物是「文件 + 指纹 + nonce + 回执」，不是「生成了一串字符」。

## 先读任务，再读版式

1. `git clone --depth 1 <bus>` 后读 `inbox/task_<ref>_*.json` —— constraints 逐条列了要写哪些字段、
   落哪个路径、回执放哪。按 constraints 写，不按记忆写。
2. 版式照抄同目录已有的 token 文件，别自创：`mcp-token-friday.md` 的分节是
   `# MCP token — <持有人>` / `签发人 … 持有人 … nonce … 指纹` / `## token`（围栏）/ `## 用法（MCP streamable HTTP）` /
   `## 实况（实测日期）` / `## 纪律`。人会对这份文件做 diff，结构变了就是噪音。
3. 这些文件是 `600`、属主 `1005`，容器 uid 10000 读不到 —— 用 root 读，并且**先打码再进上下文**：
   `ssh … "docker exec owjdxb cat /volume2/2-AI/A2A/secrets/mcp-token-friday.md" | python3 redact.py`
   （redact 规则：把 `[A-Za-z0-9_-]{24,}` 换成 `<REDACTED>`）。别人签的 token 没有理由进你的上下文。

## 生成

- nonce：`FR-MCP-` + `secrets.token_hex(3).upper()` → 6 位十六进制大写。
- token：`hive-mcp-` + `secrets.token_hex(20)`（49 字符）。
- 指纹：`<前缀>_<首4>…<末4>`，写进文件与回执；群聊和回执只引用 nonce 或指纹。
- 脚本要幂等：nonce/token 先落一份 600 的 state json，重跑复用同一枚，别签两枚。

## 落盘与验收

| 检查 | 手段 | 期望 |
|---|---|---|
| 属主/权限 | `ls -l …/secrets/mcp-token-<id>.md` | `-rw------- 1005:1005` |
| 双端一致 | 本地与 NAS 各 `md5sum` | 同一个 hash |
| nonce 在位 | `grep -n 'FR-MCP-' …` | 命中所签 nonce |
| 端点活着 | `POST /mcp` initialize | `200` + `Mcp-Session-Id` |
| 鉴权实况 | 真 / 假 / 无 token 各打一次 | 三个都 200 → 服务端不校验 |

写入用 root 容器代写（见 SKILL.md「凭据投递」），写完 `chown 1005:1005`，否则宿主侧同步与 Mac 端读不了。

## 回执

`outbox/receipt_<task_ref>_<your-id>_<YYYYMMDDTHHMMSS+0800>.json`，body 放 `token_fingerprint`、
`secrets_path`、`md5`、`format`（说明对齐了哪个既有文件）、`endpoint_test`、`auth_reality`、`delivery_gap`。
**token 值不进回执**。push 可能被双推周期顶掉，`git pull --rebase` 后重试一次即成功。

## 必说的两句实话

1. **签发 ≠ 鉴权生效。** 服务端不校验 Bearer（真/假/无 token 全 200），这枚 token 是「规范凭据 + 将来开校验即用」，
   别在回执或群里说成「已开通访问控制」。
2. **落盘 ≠ 持有人能读到。** `secrets/` 在 `.gitignore` 里、不进总线；NAS 上写了，云端或远端的 agent 依然拿不到。
   回执里点明投递缺口（BOSS 转发 / 对方本机 secrets 目录 / 一次性通道），让对方选。
