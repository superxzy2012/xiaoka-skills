# neonize（WhatsApp 协议库）实操笔记

## 客户端与事件

```python
from neonize.aioze.client import NewAClient
from neonize.aioze.events import MessageEv
from neonize.utils.jid import Jid2String, build_jid

client = NewAClient("wa.db")

async def on_qr(c, data_qr: bytes):      # 二维码事件
    ...
client.event.qr(on_qr)                    # 正确：方法注册

@client.event(MessageEv)                  # 消息事件可用装饰器
async def on_message(c, evt: MessageEv):
    src = evt.Info.MessageSource
    print(src.IsFromMe, Jid2String(src.Chat), Jid2String(src.Sender))

await client.connect()
await client.idle()
```

要点：
- **QR 回调只能用 `client.event.qr(cb)`**，装饰器形式的 QR handler 不触发（排查时会误判成「库坏了」）。
- `MessageEv` 的事件对象是 protobuf：用 `m.HasField("xxx")` 判类型，不是 `m.xxx` 直接取。

## 配对码登录（推荐）

```python
await client.PairPhone("86【手机号】", True)   # (E164 号码, 是否 phone number)
```
- 输出 8 位码（形如 `MQ39-VF1J`），在手机「已关联的设备 → 用电话号码关联」输入。
- 二维码经聊天工具转发必然过期（寿命 20~30 秒），别用。
- 成功后手机设备列表出现 `Safari (Neonize)` 之类条目，登录态写进 db，之后免扫码。

## JID 与 LID

| 形态 | 含义 |
|---|---|
| `<数字>@s.whatsapp.net` | 普通个人联系人 |
| `<数字>@g.us` | 群 |
| `<数字>@bot` | WhatsApp 内置/AI bot（Meta AI 这类） |
| `<数字>@lid` | 隐私 ID 形态；**自己账号**的 LID 常出现在 `from_me=True` 的 sender 上 |

- `Jid2String(jid)` 打印/落库用，`build_jid(user, server)` 反解发送用。
- 同一个会话，`chat` 可能是 `@bot` 而 `sender` 是 `@lid`——**配规则用 `chat`**，不要用 sender。
- 联系人表（`whatsmeow_contacts`）只包含同步到的联系人，**不等于会话列表**；目标不在表里很正常。

## 单连接约束

同一个 db / 同一个账号**同时只能有一个活跃连接**。第二个 client 登录会把第一个挤掉（`StreamReplaced`），
被挤掉的那个进程仍然活着但永远收不到消息 —— 这是「桥在线但零消息」的头号原因。

## 消息类型

常见可读类型：`conversation`、`extendedTextMessage`、`imageMessage`、`videoMessage`、`audioMessage`、`documentMessage`、`richResponseMessage`。

非内容类型（必须丢弃，否则刷屏）：
- `protocolMessage` 且 `type: AI_METADATA_OPERATION` —— AI 状态心跳（working/responding/online）。
- `protocolMessage` 且 `type: MESSAGE_EDIT` —— 若 `editedMessage.richResponseMessage` 有内容则是流式正文，否则是编辑回执。
- `messageContextInfo` —— 设备/bot 元数据。
- `status@broadcast` / `broadcast` server —— 状态广播。

## 群与联系人枚举（注意：先停桥）

```python
await client.get_joined_groups()      # 返回群列表；返回 0 不代表对象不存在
```

只读 db 的脚本（sqlite3 直查 `whatsmeow_contacts` / `whatsmeow_message_secrets` / `whatsmeow_lid_map`）
同样要**先 kill 桥**，否则连接冲突。
