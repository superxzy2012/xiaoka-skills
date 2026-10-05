# Response shapes and how to read them

Condensed from a real bot↔bot handshake in a 9-bot group. Shapes are stable; ids and
counts are per-chat.

## Send — mention parsed (the only good outcome)

`POST /open-apis/im/v1/messages?receive_id_type=chat_id`

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "message_id": "om_x100b630060a468a0c3894d2bb58c17c",
    "mentions": [{"key": "@_user_1", "id": "ou_cf77d7d5cfc3ce4c867b0d97fea352fe", "name": "", "tenant_key": ""}]
  }
}
```

`name` is frequently empty for bots — **key on `id`, not `name`.**

## Send — message posted, mention did NOT parse

Same request, but the text contained a literal `@名字` instead of the tag:

```json
{"code": 0, "data": {"message_id": "om_...", "mentions": []}}
```

`code:0` here is the trap: it means "message accepted", nothing more. The receiver never got
an `im.message.receive_v1` for an @, so a peer bot that waits to be mentioned stays silent.
Fix: recall (`DELETE /im/v1/messages/<message_id>` → `{"code":0,"data":{},"msg":"success"}`)
and resend with `<at user_id="ou_xxx"></at>`.

## Chat info — cheapest proof the app can talk at all

`GET /open-apis/im/v1/chats/<chat_id>` needs only `im:chat:readonly`:

```json
{"code":0,"data":{"name":"管理群","bot_count":"9","chat_mode":"group",
 "chat_status":"normal","chat_type":"private","owner_id":"ou_ce4e...","external":false}}
```

One call proves app identity, bot-in-chat, and group health together. `bot_count` is a
string, not an int.

Do **not** use `GET /im/v1/chats` (list the bot's groups) as a membership test — the list is
incomplete under app identity and omits chats the bot is actually in.

## Member list — the scope you will usually be denied

`GET /open-apis/im/v1/chats/<chat_id>/members?member_id_type=open_id&page_size=100`

```json
{"code":99991672,"msg":"Access denied. One of the following scopes is required:
 [im:chat:readonly, im:chat, im:chat.group_info:readonly, im:chat.members:read]."}
```

Returned as **HTTP 400 with a JSON body** — `urlopen` raises before you can `json.loads`,
so the client has to read the body off the `HTTPError`. Rather than request the scope, pull
the id out of the `[Mentioned: ... (open_id=ou_xxx)]` prefix on your own inbound log lines.

## Error codes worth memorizing

| Code | Cause | Do this |
|---|---|---|
| `99991679` | message API called with a user-identity token | exchange for `tenant_access_token` |
| `99991672` | missing chat read scope | use the log prefix instead of widening scopes |
| `230027` | missing `im:message.group_msg` (history pull) | ignore; unrelated to receiving @ |