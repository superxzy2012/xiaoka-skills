# WhatsApp 消息形态与正文抽取（neonize / NextBridge）

驱动层只处理文本类字段，其余 return。排查时先把原始报文落盘再分析，不要在日志里截断猜字段。

## 落盘探针

```python
with open("raw_msgs.log", "a") as f:
    f.write(f"\n=== {msg_id} {Jid2String(src.Chat)} ===\n{str(m)}\n")
```

## 常见形态

| 形态 | 说明 | 处理 |
|---|---|---|
| `conversation` | 普通文本 | 直接用 |
| `extendedTextMessage.text` | 带引用的文本 | 直接用 |
| `imageMessage.caption` 等 | 媒体 + 说明 | 正文取 caption，附件记类型 |
| `protocolMessage` `type: AI_METADATA_OPERATION` | Meta AI 的 agent 状态心跳（working / responding / online） | 丢弃 |
| `protocolMessage` `type: MESSAGE_EDIT` | Meta AI 流式改写自己的回复 | 取 `editedMessage.richResponseMessage.unifiedResponse.data` |
| `richResponseMessage` | Meta AI 的完整回复 | 取 `unifiedResponse.data` |
| `messageContextInfo` | 设备/bot 元数据 | 丢弃 |

## unifiedResponse.data 结构

一段 JSON 字符串，形如：

```json
{"response_id":"...","sections":[{"view_model":{"__typename":"GenAISingleLayoutViewModel",
 "primitive":{"__typename":"GenAIMarkdownTextUXPrimitive","text":"A task is waiting for your review."}}}]}
```

正文在 `sections[].view_model.primitive.text`，但不同 view_model 层级不一致，**按固定路径取会漏**。用递归收集：

```python
def extract(raw: str) -> str:
    import json
    try:
        data = json.loads(raw)
    except Exception:
        return ""
    parts = []
    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in ("text", "body", "plain_text", "plainText") and isinstance(v, str):
                    if v.strip():
                        parts.append(v.strip())
                elif k in ("title", "subtitle") and isinstance(v, str):
                    if v.strip() and len(v) < 300:
                        parts.append(v.strip())
                else:
                    walk(v)
        elif isinstance(node, list):
            for it in node:
                walk(it)
    walk(data)
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return "\n".join(out)
```

## 去重

流式输出对同一 `msg_id` 会推多条递增文本。按 `(msg_id, hash(text))` 记集合跳过重复；集合超过 2000 条时只保留最近 500 条，防止常驻进程内存缓慢增长。

## 会话 JID 与发送者 JID 可能不同

Meta AI 类账号：`chat` 是 `<数字>@bot`，但 `sender` 可能是自己的 LID（`<数字>@lid`，`from_me=True`）或对方 LID。**路由用 `chat`，不要用 `sender`**，否则同一会话会被拆成多个 channel。
