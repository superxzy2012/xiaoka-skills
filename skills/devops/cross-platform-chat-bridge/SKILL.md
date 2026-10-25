---
name: cross-platform-chat-bridge
description: Use when 要把飞书与 WhatsApp 等 IM 双向打通。
version: 1.0.0
author: 小卡
license: MIT
agent_created: true
metadata:
  hermes:
    tags: [bridge, whatsapp, feishu, nextbridge, neonize]
    related_skills: [feishu-group-bot-bridge, agent-down-doctor]
---

# 跨平台 IM 双向桥接（NextBridge + neonize）

## When to Use

- 用户要把一个飞书自建应用和一个人的 WhatsApp 账号（或其他 IM）消息**双向**转发。
- 症状类触发：「桥接发了但反向没收到」「WhatsApp 已登录但一条消息也进不来」「飞书长连接显示 connected 却收不到事件」。
- 不适用：只做飞书群内 @ 沟通 → 用 `feishu-group-bot-bridge`。

NextBridge 只做「驱动 + 规则路由」，**消息形态的差异全在驱动层，坑也全在那儿**。

## 部署（venv 直跑，不要指望 Docker）

Docker daemon 在受限沙箱里常常起不来。直接 venv 跑，所有依赖装进同一个 venv：

```bash
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
  <venv>/bin/python -m pip install neonize segno loguru lark-oapi sqlalchemy \
  pydantic aiohttp pyyaml tomli-w pillow httpx[socks] aiohttp-socks fresholm tzlocal
```

- `neonize` 依赖 **libmagic**：import 报缺库时下载 `libmagic1_<ver>_amd64.deb`，`dpkg-deb -x` 解包到本地目录，运行时设 `LD_LIBRARY_PATH=<dir>/usr/lib/x86_64-linux-gnu`。
- 启动器必须注入四个环境变量，缺一个就连不上：
  `LD_LIBRARY_PATH`、`NEXTBRIDGE_DATA_PATH`（指向含 config.json 的 data 目录）、`HTTPS_PROXY/HTTP_PROXY/ALL_PROXY`（WhatsApp 直连被墙，走本机代理）。
- 启动用 Hermes `terminal(background=true)`，**不要 `nohup`/`setsid`**（会被 shell wrapper 检查拒掉，且进程不受追踪）。

## 配对登录：用配对码，别用二维码

二维码有效期 20~30 秒，经 IM 传图必然超时（`Login event: timeout`）。用 8 位配对码，几分钟有效：

```python
await client.PairPhone("86<手机号>", True)     # 手机 > 已关联的设备 > 关联新设备 > 用电话号码关联
```

- neonize 的二维码回调注册方式是 `client.event.qr(callback)`，**不是** `@client.event.qr` 装饰器（装饰器版本永不触发）。
- 配对成功后登录态落在 `storage_dir/<name>.db`，之后免扫码；把这个 db 复制到桥的 data 目录即可复用。
- 桥启动日志的成功标志：`Successfully authenticated` + `connected`。

## 🔴 铁律：一个 WhatsApp 账号同时只能有一个连接

用同一份 db / 同一账号再起**任何**第二个 neonize 连接（哪怕只是 `get_joined_groups()` 查一下），服务端会 `StreamReplaced` 把桥挤下线，**桥会静默地收不到任何消息**，日志看起来还一切正常。

⇒ 任何要读 wa db 或另起连接的脚本，**先 kill 桥接进程，查完再重启桥接**。诊断「桥在线但零消息」时，第一个怀疑对象就是自己之前跑过的查询脚本。

## 拿对端 JID：探针，不要猜

联系人表（`whatsmeow_contacts`）经常**不含**目标对象，群列表也可能是 0 —— 别按名字匹配，也别拿号码反推。

正确做法：在驱动的入站 handler 最前面加一条**全量探针**日志（含 `from_me`、`chat`、`sender`、`id`），重启桥，让对方真发一条消息，从日志读真实 JID。

```python
logger.info(f"PROBE from_me={src.IsFromMe} chat={Jid2String(src.Chat)} sender={Jid2String(src.Sender)} id={evt.Info.ID}")
```

**`from_me=True` 的消息被驱动直接丢弃是设计行为**（只转发别人发来的）。所以在 WhatsApp 里自己打字永远测不出反向——反向验证必须让**对端回复**。

## 🔴 消息形态：NextBridge 只认文本，其余全被丢

驱动的 if/elif 分支只处理 `conversation` / `extendedTextMessage` / image / video / audio / document，**其余一律 return**。WhatsApp 官方/AI 类账号的正文往往落在别的字段里：

| 场景 | 字段 |
|---|---|
| 普通文本 | `conversation` / `extendedTextMessage.text` |
| Meta AI（认证名「AI」，JID `<数字>@bot`）直接回复 | `richResponseMessage.unifiedResponse.data` |
| 同一账号流式输出 | `protocolMessage.editedMessage.richResponseMessage.unifiedResponse.data`（`type: MESSAGE_EDIT`） |
| 状态/心跳噪声 | `protocolMessage` + `type: AI_METADATA_OPERATION`、`messageContextInfo` —— 丢弃 |

`unifiedResponse.data` 是一段 JSON 字符串，正文在 `sections[].view_model.primitive.text`。通用抽法：递归收集 key 为 `text/body/plain_text` 的字符串，去重保序。细节见 `references/whatsapp-message-shapes.md`。

**流式输出会反复推同一个 msg_id**（每条编辑一次事件）⇒ 必须按 `(msg_id, hash(text))` 去重，否则飞书侧被刷屏。

排查消息形态时，把原始报文 `str(m)` 追加落盘（`raw_msgs.log`），比在日志里截断 400 字猜字段快得多。

## rules.json：connect 型规则

```json
{"rules": [{
  "id": "<name>",
  "type": "connect",
  "channels": {
    "<wa_instance>": {"chat_id": "<数字>@bot"},
    "<fs_instance>": {"chat_id": "oc_..."}
  },
  "msg": {"msg_format": "{msg}"}
}]}
```

- 规则从 data 目录的 `rules.json` 读取，启动日志有 `Loaded N bridge rule(s)` 才算生效。
- 这个版本**没有 `validate` 子命令**（`main.py validate` 报 invalid choice），改完直接重启进程验证。
- 路由是否命中看 DEBUG 日志：`Channel match success for <instance>` → `Dispatching to <peer> channel={...}`；只出现 `on_message` 而没有后两行 = 规则没匹配上。

## 🔴 飞书侧：同一 app 的多条长连接会抢事件

反复重启桥接后，飞书事件可能**一条都进不来**，而 WS 连接日志明明显示 `connected`。原因是同一 app 存在多条长连接时飞书按连接分发事件，旧进程残留的僵尸连接会吞掉事件。

**决定性测试**（不要靠重启赌）：停掉桥接，单独跑 `scripts/feishu_ws_probe.py`（最小 lark-oapi 长连接监听器，只打印收到的消息），让对方发一条。
- 探针收到 → 桥的问题（驱动/规则），回去查 `on_message` 之后的代码。
- 探针也收不到 → app 层问题（事件订阅、权限、发版），去查开放平台配置（见技能 `feishu-group-bot-bridge` 第 1 层）。

同时用 API 单独验证**出站**：`POST /open-apis/im/v1/messages?receive_id_type=chat_id` 返回 `code 0` + `message_id` 即发送链路通；这样能把「收不通」和「发不通」彻底分开。

## 双向验收（缺一不算通）

| 方向 | 证据 |
|---|---|
| 飞书 → WhatsApp | 桥日志 `Dispatching to <wa>` 且无 `send failed`，且对端聊天里**肉眼可见** |
| WhatsApp → 飞书 | 桥日志出现 `on_message: platform: 'whatsapp'`，且飞书侧**肉眼可见** |

- 只看到 `PROBE` 没有 `on_message` = 消息进了驱动但被类型/内容分支丢弃。
- 只看到 `on_message` 没有 `Dispatching` = 规则没匹配。
- 两个都看不到 = 事件根本没到（先查连接竞争，再查账号是否被挤下线）。
- **不要让用户反复盲发测试消息**：每轮测试前先确认自己加的探针/改动已经生效（进程 PID 变了、启动日志出现新版本标志）。

## 收尾

- 桥接是常驻进程，机器重启/会话清理后要重新拉起；把启动器写成脚本（env 注入 + `exec python main.py`）。
- 凭据（app_secret）落盘 600，绝不写进脚本字面量；曾在聊天里明文出现过的 secret，跑通后提醒用户在开放平台重置。
