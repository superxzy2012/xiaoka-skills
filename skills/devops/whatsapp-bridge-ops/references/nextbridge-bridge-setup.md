# NextBridge 桥接配置与取 JID 速查

适用：NextBridge v0.3.0（源码仓 `~/cache/scratch/NextBridge`），Python 3.13 + `/opt/data/.venv-browser`。

## 1. 依赖（装到 `/opt/data/.venv-browser`）

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  /opt/data/.venv-browser/bin/python -m pip install \
  neonize loguru lark-oapi sqlalchemy pydantic aiohttp pyyaml tomli-w \
  pillow httpx[socks] aiohttp-socks fresholm tzlocal fastapi uvicorn segno
```

- 只需飞书 + WhatsApp 两个驱动时不必装 discord-py / telegram / mautrix 等重依赖。
- ⚠️ 命令里出现 `uvicorn`/`fastapi` 会被 terminal 工具判为「启动长驻服务器」而拒绝执行；把安装命令写进 `.sh` 再 `bash 脚本` 跑。
- `import magic` 缺 libmagic 时，先 `ctypes.CDLL(...libmagic.so.1)` 再 import（见 `scripts/pair_code.py` 头部）。

## 2. `data/config.json`

```json
{
  "global": {
    "proxy": "http://192.168.199.2:7891",
    "http": { "enable": "false" },
    "log": { "level": "INFO", "dir": "data/logs" }
  },
  "feishu": {
    "fs_muse": {
      "app_id": "cli_xxx",
      "app_secret": "xxx",
      "use_long_connection": true
    }
  },
  "whatsapp": {
    "wa_muse": { "storage_dir": "/abs/path/data/wa_muse.db" }
  }
}
```

- 顶层结构固定两层：`<平台名> → <实例ID> → 驱动配置`。实例 ID 是自定义的，规则里引用它。
- 每个驱动的配置模型是 `extra="forbid"`，**写错键名直接启动失败**，报 `Config error in <platform>.<inst>`。
- 飞书长连接模式不需要公网回调，所以 `http.enable` 设 `"false"`（三态字符串：`unset` / `true` / `false`）。
- 代理也可只靠环境变量（`http_proxy` / `https_proxy` / `all_proxy`），写在 `global.proxy` 更明确；想强制不走代理填 `disabled`。

## 3. `data/rules.json`

```json
{
  "rules": [
    {
      "id": "wa-feishu-bridge",
      "type": "connect",
      "channels": {
        "wa_muse": { "chat_id": "【手机号】47697@bot" },
        "fs_muse": { "chat_id": "oc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" }
      },
      "msg": { "msg_format": "{msg}" }
    }
  ]
}
```

- `connect` = 双向互联（任一频道收到的消息转发给其余全部）；`forward` = 单向 `from` → `to`。
- 频道键：飞书 `chat_id`、WhatsApp `chat_id`(JID)、Telegram `chat_id`、QQ `group_id`、Discord `server_id`+`channel_id`。
- 可选 `match.keywords` / `match.users.include|exclude` 做来源过滤。
- `msg_format` 模板变量：`{platform}` `{instance_id}` `{user}` `{user_id}` `{msg}` `{time}` `{username}`。飞书/钉钉会把 `<richheader title content/>` 渲染成 `[title · content]` 纯文本前缀。
- **回声防护**：默认（`strict_echo_match=false`）目标实例 ID 或频道与来源相同就跳过，这正是防止「转回来又转回去」的机制，不要关。

## 4. 启动脚本（固定套路）

```bash
cd /path/NextBridge
export LD_LIBRARY_PATH=/opt/data/local/libmagic/usr/lib/x86_64-linux-gnu
export HTTPS_PROXY=http://192.168.199.2:7891
export HTTP_PROXY=http://192.168.199.2:7891
export ALL_PROXY=http://192.168.199.2:7891
export NEXTBRIDGE_DATA_PATH=/path/NextBridge/data
exec /opt/data/.venv-browser/bin/python main.py
```

写成 `.sh` 用 `terminal(background=true)` 跑，输出重定向到日志文件；改配置后必须整进程重启（`rules` 支持 SIGHUP 热重载，但驱动配置不行）。

## 5. 取 JID：离线 SQL（不占 WhatsApp 连接）

```sql
-- 联系人（含已同步的通讯录名）
SELECT their_jid, first_name, full_name, push_name FROM whatsmeow_contacts;
-- LID ↔ 手机号映射（WhatsApp 新版常用 @lid 寻址）
SELECT lid, pn FROM whatsmeow_lid_map;
-- 近期有过消息的会话
SELECT DISTINCT chat_jid, sender_jid FROM whatsmeow_message_secrets;
```

JID 形态：私聊 `8613xxxxxxxxx@s.whatsapp.net`、群 `1203630xxxxxxxx@g.us`、官方/认证机器人 `<数字>@bot`、新式隐私地址 `<数字>@lid`。

## 6. 排障对照

| 现象 | 原因 | 处理 |
|---|---|---|
| 进程活着但没二维码 | 代理没设，握手静默挂死 | 加 `ALL_PROXY`，重跑 |
| `Successfully authenticated` 后立刻 `StreamReplaced` | 同账号被第二个连接顶掉 | 只保留一个进程 |
| 飞书侧收到消息但 WhatsApp 没发出 | 规则 `chat_id` 不对 / 没加载 rules | 看 `Loaded N bridge rule(s)` 和 `No sender registered for instance` |
| 自己发的消息桥接毫无反应 | 驱动过滤 `src.IsFromMe` | 属正常；要探针见 SKILL.md |
| `Config error in whatsapp.wa_muse` | 配置键名拼错（extra=forbid） | 对照本文第 2 节 |
| 媒体发不出、文字正常 | 缺 ffmpeg | `apt` 装不了就接受，或装静态 ffmpeg 到 PATH |
| 飞书日志有 `[WS] connected` 但零条 `on_message` | 用户发给了别的 bot / 事件没投递到这条连接 | 见 SKILL.md「飞书『发出正常、收不到』的三步定位」 |
| 飞书 API 发消息 `code:0`，客户端也收到了，桥接仍无入站 | 问题锁死在入站侧 | 停桥接 → `scripts/feishu_inbound_probe.py --listen` 判事件是否到达 app |
