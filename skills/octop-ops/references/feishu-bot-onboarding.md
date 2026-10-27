# Octop 接飞书：扫码创建机器人

Octop 自带飞书官方「扫码创建应用」能力，走 OAuth 2.0 Device Authorization Grant（RFC 8628，`lark_oapi.register_app`，需 `lark-oapi>=1.5.5`），不需要先去开放平台手搓应用、也不需要人工填 app_id/app_secret。

## 一、相关代码（读源码定位，别反复摸）

| 文件（容器内 `/app/src/octop/`） | 作用 |
|---|---|
| `infra/gateway/bot_creators/feishu_bot_creator.py` | 子进程本体：发起设备授权 → 吐二维码 URL → 轮询到 `app_id`/`app_secret` |
| `infra/gateway/bot_creators/feishu_runner.py` | `start/poll/stop` 包装，把 stdout 的 JSONL 事件解析成 `qr_url`/`app_id`/`app_secret`/`status` |
| `cli/support/feishu_creator.py` | CLI `feishu-setup`：起子进程 → 终端画 ASCII 二维码 → 拿到凭据后 PATCH/POST channel |
| `cli/commands/channel.py` | `channel` 子命令族（list/get/create/patch/delete/test/bind-group/bind-qq/bind-wecom/bind-weixin） |

`--platform feishu` 走 `open.feishu.cn`，`--platform lark` 走 `open.larksuite.com`；`state_file_prefix` 分别是 `octop-feishu-bot` / `octop-lark-bot`，状态落 `/tmp`。

## 二、拿一个能发给人的二维码（已实测）

```bash
# 1) 容器内后台起 creator
ssh DY@192.168.199.2 "sudo -n docker exec -d octop sh -c 'cd /app && /app/.venv/bin/python3 -m octop.infra.gateway.bot_creators.feishu_bot_creator create > /tmp/feishu_creator.log 2>&1'"
sleep 8
# 2) 读 JSONL，取 show_qrcode 的 content.url
ssh DY@192.168.199.2 "sudo -n docker exec octop sh -c 'cat /tmp/feishu_creator.log'"
```

日志形如：

```json
{"action":"show_qrcode","level":"info","step":"login","ts":1793031916,
 "content":"{\"url\": \"https://open.feishu.cn/page/launcher?user_code=XXXX-XXXX&from=sdk&tp=sdk&source=python-sdk%2Foctop&desc=…&createOnly=true\", \"expire_in\": 3600}"}
```

- `content` 是**被转义的 JSON 字符串**，要再 `json.loads` 一次。
- `expire_in` 单位是**秒**（实测 3600），不是分钟。
- `createOnly=true` = 这次扫码只创建新应用，不会挂到已有应用上；应用名在扫码后的确认页填。
- 之后每 5 秒一行 `Waiting for scan confirmation...`，说明进程在正常轮询。

渲染成 PNG（容器外，`segno` 纯 Python、原生写 PNG、无依赖）：

```python
import segno
segno.make(url, error='m').save(path, scale=12, border=4)
```

`pip install segno` 即可；系统 python 和 `/opt/data/.venv-browser` 都能装（该 venv 有 pip）。

## 三、坑

1. **别转发别处存下来的二维码图片。** 扫码链接按 `user_code` 一次性生成、有 `expire_in`，几分钟前抓的图基本已失效。每次现拉现发，并把有效期（北京/UTC 都说清）告诉用户。
2. **`docker exec -d … sh -c '…'` 嵌在 ssh 双引号里会静默失败**：命令没起来也返回 0、输出为空。判活只看 `/tmp/feishu_creator.log` 有没有 `show_qrcode`，不看返回码。
3. **进程要挂着等扫码。** creator 会一直轮询；前台 `docker exec` 会被客户端超时杀掉，二维码当场失效。
4. **扫码 ≠ 接完。** 拿到 `app_id`/`app_secret` 后还要三步：绑 channel（`feishu-setup` 自动 PATCH/POST；手搓走 `/api/channels`）→ 开放平台确认 scope（`im:message`、`im:message:send_as_bot`、`im:chat:readonly`）→ 配事件订阅**长连接**。scope 缺的表现是发消息受限、读不到群，报 `99991672` / `230027`；同一租户下别的 bot（如小豆）缺 `im:*` 是**同一面墙同一次授权**，进 console 一次点完即可。

## 四、验证边界

- 「拉起 creator → 取 URL → 渲染 PNG → 有效期 3600s」这一段**已实测**。
- 扫码之后的**凭据回收与 channel 绑定只读过源码，未端到端验证**。首次真跑通后，把实际返回字段、channel 落库形状、以及扫码失败时的报错补进本节，别把它当成已验证流程对外承诺。
