# Anthropic /v1/messages 适配层（把 OpenAI-only 网关喂给 Claude Code）

## 何时需要

上游只出 OpenAI 协议（Chat2API、各类 web→API 项目），客户端只会说 Anthropic 协议（Claude Code、Anthropic SDK）。中间加一层薄 Flask 服务做双向翻译，比改上游或换上游便宜得多。

已落地形态：容器 `c2atools`（NAS，宿主 `8321` → 容器 `8081`），代码 `/opt/data/cache/scratch/c2atools/app.py`，镜像 `c2atools:1.0`。

## 请求映射（Anthropic → OpenAI）

| Anthropic | OpenAI |
|---|---|
| `system`（str 或 text blocks） | 首条 `{role:'system'}` |
| `messages[].content` 为 str | `{role, content}` |
| content block `{type:'text'}` | 拼进 `content` |
| content block `{type:'tool_use', id, name, input}` | `assistant.tool_calls[{id, type:'function', function:{name, arguments: json.dumps(input)}}]`，`content` 置 `null` |
| content block `{type:'tool_result', tool_use_id, content}` | 独立的 `{role:'tool', tool_call_id, content}`，**排在 user 文本之后** |
| `tools[{name, description, input_schema}]` | `tools[{type:'function', function:{name, description, parameters: input_schema}}]` |
| `tool_choice: {type:'auto'}` | `'auto'`（对象形式上游不认） |

坑：`tool_result` 必须拆成独立 `role:tool` 消息，塞进 user 文本里模型就当普通内容读，永远不再调工具。

## 响应映射（OpenAI → Anthropic）

```json
{"id":"msg_<rand>","type":"message","role":"assistant","model":"<req model>",
 "content":[{"type":"text","text":"..."},
            {"type":"tool_use","id":"<上游 id>","name":"...","input":{...}}],
 "stop_reason":"tool_use|end_turn","stop_sequence":null,
 "usage":{"input_tokens":prompt_tokens,"output_tokens":completion_tokens}}
```

有 `tool_calls` → `stop_reason="tool_use"`；`arguments` 解析失败时兜 `{"_raw": <原串>}`，别抛 500。`content` 为空数组时补一个空 text block，Claude Code 会崩在空 content 上。

## 流式

上游先按非流式拿完整结果，再一次性发合规的 Anthropic SSE 事件序列：`message_start` → 每块 `content_block_start` + `content_block_delta`（文本用 `text_delta`，工具用 `input_json_delta` 的 `partial_json`）+ `content_block_stop` → `message_delta`（带 `stop_reason`）→ `message_stop`。Claude Code 不要求逐 token，只要求事件序列合法。

## 复用上游已有管线（关键技巧）

不要重写一份工具注入/解析逻辑。上游网关已有 `chat_completions()` 视图时，用 Flask 的测试上下文直接调它：

```python
def _call_pipeline(openai_body):
    openai_body['stream'] = False
    with app.test_request_context('/v1/chat/completions', method='POST', json=openai_body):
        resp = chat_completions()          # 复用压缩/注入/解析/fallback 全链路
    r, status = (resp[0], resp[1]) if isinstance(resp, tuple) else (resp, 200)
    return (r.get_json() if hasattr(r, 'get_json') else json.loads(r)), status
```

模型名映射：Claude Code 会传 `claude-sonnet-4-5` 之类，适配层里 `startswith('claude-')` 或 `in ('deep','fast','default')` 一律改写成上游真实模型名，否则上游 404。

## 验收（三件都过才算通）

1. 带 `tools` 的 `/v1/chat/completions` → `choices[0].message.tool_calls` 有结构。
2. 带 `tools` 的 `/v1/messages` → `stop_reason:"tool_use"`，`content` 里有 `tool_use` block 且 `input` 已解析成对象。
3. 多轮：assistant `tool_use` + user `tool_result` 回传后，返回 `stop_reason:"end_turn"` 且文本正确复述工具结果；再验一次 `stream:true` 事件序列完整。

## 观察到的副作用

模型可能把注入的工具提示词误判成「文件内容里的注入文本」并在回复里点名（说明提示词位置显眼但无害）。要消掉就把工具说明放 `system` 最前，并去掉「【系统提示】」这类伪装标记。
