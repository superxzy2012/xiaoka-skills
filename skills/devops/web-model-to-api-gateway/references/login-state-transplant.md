# 跨机复用网页端登录态（Electron / Chat2API）

## 何时用

目标机器不想或不能重登，而源机器上同一套 Electron 壳（含改名换皮版）已经登录过。前提是两端同源——先用 bundle id 确认（见 SKILL.md「先认脸，再决策」）。

## 三条铁律

1. **只搬令牌，不搬 cookie 文件本体，不碰钥匙串。** 把 refresh token / JWT 粘到目标端的「供应商 → 手动输入凭证」，让它自己重新换发会话。搬 `Cookies` sqlite 过去既没必要（会话本来就要换发），又把设备指纹类 cookie 一起带过去，风控更敏感。
2. **别看到 `encrypted_value` 就断言「加密了搬不了」。** Chromium 的 cookie 是混存：同一分区里 refresh token 常在明文 `value` 列，access token 才是密文（`value` 长度为 0）。先量长度再下结论——这一条误判会直接否掉整条正确路线。
3. **「验证成功 / 账户在线」≠ 能出话。** 必须发一条真实 `/v1/chat/completions` 并检查 `choices[0].message.content` 非空。

## 读源机器（macOS）

userData 在 `~/Library/Application Support/chat2api`；每个供应商一个分区目录 `Partitions/<part>/Cookies`。用只读 URI 打开，避免锁住正在运行的 app：

```bash
sqlite3 "file:$HOME/Library/Application Support/chat2api/Partitions/glm-session/Cookies?mode=ro" \
  "select host_key,name,length(value),length(encrypted_value) from cookies where name like '%token%' order by length(value) desc;"
```

批量列全部 Token 类 cookie 用 `scripts/dump_electron_cookies.py <userData目录>`（只读，输出 host/name/value长度/是否形如 JWT）。

需要判断有效期时解 JWT 第二段：base64url 补齐 `=` 后解 JSON 取 `exp`（秒级时间戳）。

## 各厂商令牌落点（实测）

| 分区 | cookie 名 | 类型 | 可用性 |
|---|---|---|---|
| `glm-session` | `chatglm_refresh_token` | refresh token | ✅ 可注入，验证通过 |
| `oauth-<ts>`（智谱） | `chatglm_token` + `chatglm_token_expires` | access token | ⚠️ 多为密文，别指望 |
| `oauth-<ts>`（MiniMax） | `_token`（host `agent.minimax.cn`） | JWT | ✅ 可注入 |
| `oauth-<ts>`（Qwen） | `token`（host `.qwen.ai`） | JWT | 看 `exp`，过期就废 |
| `oauth-<ts>`（MiMo） | `passToken` / `xiaomichatbot_serviceToken` | 明文 | 未验，可试 |
| `kimi-session` | 各家自定义 | — | 未验 |
| DeepSeek | 无对应分区 | — | 只能扫码 |

分区名里的 `oauth-<ts>` 是毫秒时间戳，每次登录会变，别按名字硬编码匹配，按 `host_key` 认厂商。

## 注入到目标端（Playwright over CDP）

导航：`供应商` → `添加供应商` → 选厂商 → `下一步` → 填令牌 → `验证凭证` → 等 8~9s → `添加账户`。

```python
el = pg.query_selector('input[placeholder="请输入智谱清言刷新令牌"]')   # 用 placeholder 精确匹配，别用索引
el.evaluate("e => e.focus()")
pg.keyboard.insert_text(token)          # fill() 对 React 受控输入常静默失败
pg.get_by_text("验证凭证", exact=True).first.evaluate("e => e.click()")
time.sleep(8)
pg.get_by_text("添加账户", exact=True).first.evaluate("e => e.click()")
```

要点：

- 弹窗/对话框打开时点背后的导航按钮会被遮罩吃掉 → 先进对页面再开弹窗；进错页先点「返回供应商列表」重来。
- 按钮一律 `evaluate("e => e.click()")`，绕开 actionability 检查。
- 表单字段随厂商变（GLM 要刷新令牌、MiniMax 要 JWT），先 dump `input,textarea` 的 `[type, placeholder]` 再写选择器。

## 失效判据（别把上游问题当成搬运失败）

| 现象 | 含义 | 处置 |
|---|---|---|
| 上游 200 但 `content` 空 | 网页端加了签名/设备指纹校验，令牌有效、会话不被接受 | 别再重搬，去查上游请求签名 |
| 401 | 令牌 scope 不含聊天接口（或令牌类型不对） | 换另一类 cookie 试 |
| 验证凭证就失败 | 令牌过期/被吊销 | 只能重登 |

源机器上同一个上游报 500，说明问题在上游协议层而非部署——**同源的两端故障是同步的**，不要靠「换一台机器试试」来排障。

## 附：跨平台换 app.asar 升级内核

`app.asar` 是纯 JS 打包，Mac/Windows 版比 Linux release 新时可以直接搬（实测 1.6.0 内核跑在 1.4.0 的 Linux Electron 运行时上正常，模型列表随之从 `GLM-5.1` 变成 `GLM-5.3`）。

前置检查：解析 asar header，统计 `.node` 原生模块与 `unpacked` 数量——**有原生模块就不能跨平台换**（ABI 不匹配）。

```python
import struct, json
f = open('app.asar', 'rb'); d = f.read(16)
_, _, _, hlen = struct.unpack('<4I', d)
header = json.loads(f.read(hlen))
```

换完重启即可，userData（已加账号、令牌）不在 asar 里，不受影响；容器内留一份 `.old` 便于回滚。
