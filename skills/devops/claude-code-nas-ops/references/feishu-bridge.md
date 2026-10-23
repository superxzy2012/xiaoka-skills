# 给 claude-code-nas 配飞书入口

目标：BOSS 在飞书里直接跟 NAS 上的独立 Claude Code 说话（不用开网页）。
NAS 在 NAT 后无公网 IP ⇒ **只能走长连接 WebSocket**，不能用 webhook 回调地址。

## 架构

```
飞书用户 → 飞书服务器 → WebSocket 长连接 → claude-feishu-bridge 容器
                                              ↓ HTTP POST /api/chat
                                        claude-code-nas 容器
                                              ↓
                                        写 /workspace（宿主可见）
```

两个容器在同一个 compose 网络 `claude-code_default` 里，桥用容器名当 DNS：`http://claude-code-nas:3000`。

## 文件（NAS `~/claude-feishu/`）

| 文件 | 要点 |
|---|---|
| `server.js` | `@larksuiteoapi/node-sdk` 的 `WSClient` + `EventDispatcher`，注册 `im.message.receive_v1` |
| `package.json` | 只依赖 `@larksuiteoapi/node-sdk` |
| `Dockerfile` | `node:20-bookworm-slim` + `npm install --omit=dev` |
| `docker-compose.yml` | `restart: unless-stopped`、`env_file: .env`、`networks: external: claude-code_default` |
| `.env`（600） | `FEISHU_APP_ID` / `FEISHU_APP_SECRET` / `CC_TOKEN`（从 `~/claude-code/.cc_token` 取） |

## server.js 必须有的五个细节

1. **去重**：按 `message.message_id` 记 Set（超过 500 条清空），飞书长连接会重投。
2. **过滤自己**：`sender.sender_type === 'app'` 直接 return，否则 bot 自己发的消息也会触发。
3. **群聊要 @ 才理**：`chat_type === 'group'` 时要求 `message.mentions` 非空；私聊（p2p）一律回。
4. **剥 @ 占位符**：文本里是 `@_user_1` 这种占位符，用 `.replace(/@_user_\d+/g,'').replace(/@_all/g,'')` 清掉再送模型。
5. **两段式回复**：先秒回「🎩 收到，开始想了…」，再发结果。Claude 一次可能跑 30–120s，只回一条会让用户以为死了。结果超长按 7000 字截断（飞书文本消息有上限）。

回复用 `client.im.message.create({params:{receive_id_type:'chat_id'}, data:{receive_id, msg_type:'text', content: JSON.stringify({text})}})`；
要引用原消息用 `client.im.message.reply`。

## 应用侧核查：不用打开控制台

BOSS 建好应用给了 app_id/secret 后，用 open API 一次性确认「权限够不够、事件订了没、发版了没」：

```bash
# 1) 换 tenant_access_token
curl -s -X POST 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal' \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"cli_xxx","app_secret":"xxx"}'

# 2) 机器人本身在不在、叫什么
curl -s 'https://open.feishu.cn/open-apis/bot/v3/info' -H "Authorization: Bearer $TK"

# 3) 应用信息（含 owner.owner_id —— 这是 BOSS 在本应用视角的 open_id，后面建测试群要用）
curl -s 'https://open.feishu.cn/open-apis/application/v6/applications/<app_id>?lang=zh_cn' -H "Authorization: Bearer $TK"

# 4) 版本详情：scopes 列表 + events 列表 + status
curl -s 'https://open.feishu.cn/open-apis/application/v6/applications/<app_id>/app_versions?lang=zh_cn&page_size=5' -H "Authorization: Bearer $TK"
```

判读：
- `scopes` 里要有 `im:message.p2p_msg:readonly`、`im:message.group_at_msg:readonly`、`im:message:send_as_bot`。
- `event_infos[].event_type` 要含 `im.message.receive_v1`。
- `status: 1` + `publish_time` 非空 = 已发布。

> 唯一 API 查不到的是**订阅方式是否为「长连接」**，那个只能在开放平台「事件与回调 → 订阅方式」里看。
> SDK 启动日志会打印一段提示文字，出现它不代表配置错了，别据此下结论。

## 测试顺序（自己先测，别把活推给 BOSS）

1. **桥 → Claude 这段自己测**：写个 node 脚本 `docker cp` 进桥容器跑，POST `http://claude-code-nas:3000/api/chat?token=$CC_TOKEN`，看 `{"reply":"done"}` 且文件真落盘。（`node:*-slim` 没有 curl。）
2. **发消息这段自己测**：用 app 信息里的 `owner.owner_id` 建个测试群把 BOSS 拉进来，再往群里发一条招呼：
   ```bash
   POST /open-apis/im/v1/chats?user_id_type=open_id
   {"name":"<bot名> 测试","user_id_list":["<owner_open_id>"],"chat_mode":"group","chat_type":"private"}
   ```
   需要 `im:chat:create` 权限。返回 `chat_id` 后 `POST /im/v1/messages` 发一条，`code 0` 即证明发送链路通。
3. **收消息这段只能真人测**：让 BOSS 在群里 @ 一句或私聊一句，然后 `docker logs claude-feishu-bridge` 里找 `RECV` → `DONE`。
   只有走到这一步才能说「已实测通」，前面都只是「配置齐了」。

## 坑

- **`230002 Bot/User can NOT be out of the chat`**：机器人不在目标群里。别往 BOSS 和别的 bot 的私聊 `chat_id` 发消息，那个群没有本 bot。
- **飞书 open_id 是应用维度的**：从别处抄来的 `ou_...` 在本应用视角无效。本应用视角的 BOSS open_id 只能从 `application/v6` 的 `owner.owner_id` 或群成员接口拿。
- **群聊不 @ 就不触发**：`im.message.receive_v1` 在群里只推 @ 机器人的消息，所以代码里判断 `mentions` 只是双保险，不是触发条件。
- **没有 curl 的镜像**：见上，用 node 脚本 + `docker cp`。
- **凭证只落 `.env`（600）**：app_secret 不进镜像、不进代码、不打印。
