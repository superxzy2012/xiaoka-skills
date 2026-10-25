# WhatsApp 入站消息类型（neonize / whatsmeow 原始 protobuf）

判断「对方回了、桥接没转发」时，先把 `drivers/whatsapp.py` 的 `else` 分支改成**全量落盘** `str(m)`（不要截断——截断几百字正好把正文切掉），跑一条真消息，再看落下来的报文长什么样。下面是实测见到的三类形态。

## 1. 普通私聊文本（驱动已覆盖）

```
conversation: "测试"
```

或

```
extendedTextMessage {
  text: "测试"
}
```

## 2. 噪音：bot 的状态心跳

认证/官方 bot（`@bot` JID，例如 Meta AI）在生成回复期间会持续推送这类报文，**没有正文，必须忽略**：

```
protocolMessage {
  type: AI_METADATA_OPERATION
  aiMetadataOperation {
    hatchMetadataSync {
      data: "{\"version\":1,\"type\":\"event\",\"payload\":{\"event\":\"agent.status\",\"payload\":{\"activity_code\":\"working\",\"activity_text\":\"...\",\"agent_id\":\"...\"}}}"
    }
  }
}
```

`activity_code` 常见 `working` / `responding` / `online`。一条回复会刷十几条，别当成消息。

## 3. 噪音：上下文信息

```
messageContextInfo {
  deviceListMetadata { }
  botMetadata { botInfrastructureDiagnostics { } }
}
```

## 4. 正文：富响应 + 消息编辑

真正的回复体在这里，`editedMessage` 是流式多次编辑的同一条消息：

```
protocolMessage {
  key { remoteJID: "85440656879774@lid"  fromMe: true  ID: "3EB0..." }
  type: MESSAGE_EDIT
  editedMessage {
    richResponseMessage {
      messageType: AI_RICH_RESPONSE_TYPE_STANDARD
      unifiedResponse {
        data: "{\"response_id\":\"...\",\"sections\":[{\"view_model\":{\"__typename\":\"GenAISingleLayoutViewMod...\"}}]}"
      }
    }
  }
}
```

要点：

- `key.remoteJID` 是 `<lid>@lid`，**不是**会话的 `@bot` JID；会话身份仍以 `src.Chat` 为准。
- `unifiedResponse.data` 是一段 JSON **字符串**，正文散在 `sections → view_model` 的树里，键名不固定。
- 同一条消息会被反复 `MESSAGE_EDIT` 覆盖，按 `Info.ID` 去重、只转最后一次，否则飞书侧会收到一串半截内容。

### 抽取函数（递归找文本键）

```python
import json

def extract_rich_text(raw: str) -> str:
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

接入点（`_handle()` 的 `else` 分支，覆盖驱动原有的 `conversation`/`extendedTextMessage`/`imageMessage`/... 都不匹配的情况）：

```python
if m.HasField("protocolMessage") and m.protocolMessage.HasField("editedMessage"):
    inner = m.protocolMessage.editedMessage
    if inner.HasField("richResponseMessage"):
        text = self._extract_rich_text(inner.richResponseMessage.unifiedResponse.data)
```

⚠️ 这段结构是从真实报文确认的，但**富文本解析接入后必须端到端验证一次**（WhatsApp 回一句 → 飞书真收到），验证前不要对用户报「反向已通」。

## 全量探针（定位到底是没事件还是被分支丢弃）

在 `_handle()` 最开头、`if src.IsFromMe: return` 之前加：

```python
from neonize.utils.jid import Jid2String
try:
    logger.info(
        f"WhatsApp [{self.instance_id}] PROBE from_me={src.IsFromMe} "
        f"chat={Jid2String(src.Chat)} sender={Jid2String(src.Sender)} id={evt.Info.ID}"
    )
except Exception:
    pass
```

读到 `from_me=True` 就说明这是**你自己**发的（设计上不转发），读到 `from_me=False` 却没有 `on_message` 才是类型分支的问题。
