---
name: whatsapp-bridge-ops
description: Use when 桥接 WhatsApp（配对码/二维码登录、飞书桥接、排障）。
---

# WhatsApp 桥接（NextBridge / neonize）

## When to Use

- 需要把 WhatsApp 与飞书/其他平台双向互通（NextBridge）。
- WhatsApp 需要首次登录配对，或已有登录态失效需重配。
- 桥接已建但消息不通 / 只单向通 / 对方收不到。

## 环境事实
- NextBridge 源码仓：`/opt/data/cache/scratch/NextBridge`（飞书 driver 已调通，WhatsApp driver 走 neonize 0.5.2）。
- neonize 装在 `/opt/data/.venv-browser`；跑桥接/配对脚本一律显式调 `/opt/data/.venv-browser/bin/python`。
- 沙箱无 Docker daemon（只有 CLI 无 socket）：容器化方案跑不通，直接本机 venv 跑。

## 配对流程

### 路径 A（首选）：8 位配对码，不扫码

二维码只有约 30 秒寿命，而图要先经聊天软件传到用户手机再打开扫——经常来不及，症状是「扫了又让扫，最后失效」。配对码有效期数分钟，容错高得多。

1. **永远带代理跑**：WhatsApp 握手服务器被墙，直连会**静默挂死**（无报错、无二维码，进程活着但不工作）。启动时设 `HTTPS_PROXY=HTTP_PROXY=ALL_PROXY=http://192.168.199.2:7891`。
2. 后台跑 `scripts/pair_code.py <国家码+号码>`（terminal 工具 background=true）。它在 neonize 首次吐出二维码的瞬间调 `await client.PairPhone(phone, True)` 换 8 位码，日志打 `PAIR-CODE-BEGIN xxxx-xxxx PAIR-CODE-END`。
3. 把码发给用户，让他走 WhatsApp「设置 → 已关联设备 → 关联设备 → **使用手机号码关联**」。
4. 判定登录：日志出现 `CONNECTED-EVENT` → `LOGIN-PERSISTED`，db 体积明显增长（>100KB）。
5. 登录态落在 sqlite，之后重启免配对；把它复制进 NextBridge 数据目录当 `storage_dir` 即可复用（**不要再配一次**）。

### 路径 B（备选）：扫码
1. 后台跑 `scripts/pair_local.py`：生成新鲜二维码 PNG + 终端字符码。
2. PNG 一出来立刻发用户，让用户先停在「已关联设备」页面再看图。
3. 出现 `Login event: timeout` 或 `Error sending close to websocket ... EOF` = 没赶上，重来。

### 两条路径共用
- 重发新码前**必须清场**：kill 旧进程 + `rm` 掉旧 db 和旧 PNG，再重启——否则复用过期会话拿到的还是死码。
- 启动 NextBridge 主进程时同样带代理；ffmpeg 缺失只影响媒体（贴纸/语音/缩略图），文字桥接不受阻，可后补。

## 坑位
- **前台命令里用 `&` 会被 terminal 工具直接拒绝**——长驻进程一律 background=true。
- **kill 配对进程别用 `pkill -f 脚本名`**：grep 模式会匹配到执行它的 shell 自身，把自己 SIGTERM 掉。用 `ps aux | grep wa_pair | grep -v grep | awk '{print $2}' | xargs -r kill`。
- **neonize import 依赖 libmagic，沙箱没有且无 root**：`scripts/pair_local.py` 里已内置借位加载——先 `ctypes.CDLL('/opt/data/local/libmagic/usr/lib/x86_64-linux-gnu/libmagic.so.1')` 再 import（该 .so 是从清华 deb 镜像 `dpkg-deb -x` 解出来的，丢失就重下 `libmagic1_5.44-3_amd64.deb`）。若换新脚本 import neonize 前必须复制这段。
- **沙箱没有 uv**：装包用 `/opt/data/.venv-browser/bin/python -m pip install`，配 `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`。
- **日志里的终端二维码转 PNG 用 `scripts/render_qr_from_log.py`**：它做半块字符→像素还原 + 黑白反转（终端亮块在深底，标准码必须黑块白底，不反转扫不出来）；neonize 的 QREv 回调里 segno 直接存 PNG 时偶发静默失败，转日志是兜底路径。
- **🔴 `@client.event(QREv)` 装饰器对二维码不生效**：QR 走的是 `client.event._qr` 这个专用回调，装饰器只往 `list_func` 注册，永远不会被调用。症状是「终端照常打出二维码，但我的回调一行没跑」——配对码因此也拿不到。正确写法：`client.event.qr(async_fn)`，签名 `(client, data_qr: bytes)`。
- **🔴 同一账号不能同时开两个 neonize 连接**：桥接在跑时再起一个脚本连同一个 db 去列群/列联系人，会把握手挤掉（`Got replaced stream error` / `StreamReplaced` + `Error reading from websocket ... EOF`），此后**所有入站消息静默丢失**，用户会说「我发了你没收到」。取信息优先离线读 sqlite；确实要连就先停桥接，连完再起。
- **群列表为空 ≠ 没连上**：`await client.get_joined_groups()` 返回 0 只说明没进群，目标常在私聊里。别为此反复重连。

## NextBridge 桥接（飞书 ↔ WhatsApp）

完整配置模板、依赖清单、取 JID 的 SQL 见 `references/nextbridge-bridge-setup.md`。要点：

1. 用 `NEXTBRIDGE_DATA_PATH=<绝对路径>` 指定数据目录，程序只在该目录找 `config.json` / `rules.json`。
2. 飞书走长连接免公网回调：`feishu.<id>.use_long_connection: true` + `global.http.enable: "false"`（无 webhook 驱动时不必起 HTTP 服务）。
3. WhatsApp 复用已配对 db：`whatsapp.<id>.storage_dir: <绝对路径>/wa_muse.db`。
4. `rules.json` 用 `connect` 类型做双向互通，频道键统一是 `chat_id`。
5. 启动日志出现这三行才算通：`Loaded N bridge rule(s)` + `Feishu [...] [WS] connected to wss://***` + `WhatsApp [...] connected`（其前应有 `Successfully authenticated`）。
6. 本版（v0.3.0）**没有 `validate` 子命令**，只有 `convert`；配置错误只在启动时报 `Config error in <platform>.<inst>`。

### 飞书「发出正常、收不到」的三步定位

日志里 `Feishu [...] [WS] connected` 只证明**握手**成功，不证明事件会投递过来。出现「用户说发了、日志零条 `on_message`」时按下面顺序切，别反复重启碰运气（用 `scripts/feishu_inbound_probe.py`）：

1. **确认用户发的是这个机器人**：`application/v6/applications/<app_id>` 取 `app_name`，把这个名字报给用户让他核对。用户很可能在跟**另一个** bot（比如常驻的助理 bot）私聊，那条消息永远不会到桥接这里。同一次调用里看 `callback_info.callback_type` 应为 `websocket`。
2. **证明发送权限没问题**：`im/v1/messages?receive_id_type=chat_id` 往目标 `chat_id` 发一条自检文本，返回 `code: 0` 就说明 app 身份、chat_id、发消息权限都对——于是问题被锁死在**入站**。用户也能在客户端看到这条，顺带确认会话是同一个。
3. **用最小监听器判入站**：先停桥接主进程（同一 app 别留两个消费者），跑 `--listen`，让用户在**刚收到自检消息的那个会话**里发一句。收到 `EVENT chat_id=...` = app 事件订阅正常、问题在 NextBridge 驱动侧；一条都收不到 = 卡在飞书投递层，此时才去查事件订阅与长连接占用。

- `im/v1/chats` 返回空列表 **不是报错**：私聊型机器人本来就不在任何群里。
- 同一 app 的多条长连接会互相抢事件投递，被 kill 的旧进程其服务端连接可能还没过期；排查入站时先把桥接停干净再起监听器，别让两套并存。

### 取对端 JID（按成本排序）
1. **离线读 db（零风险）**：sqlite 查 `whatsmeow_contacts`（their_jid / full_name / push_name）、`whatsmeow_lid_map`（lid→手机号）、`whatsmeow_message_secrets`。不占连接。
2. **让对方先发一条**：桥接日志会打 `on_message: ... channel: {'chat_id': ...}`，这是权威值。
3. **临时探针**：驱动 `_handle()` 开头是 `if src.IsFromMe: return` —— **你自己发出的消息永远不入日志**，所以「我发了一条它没反应」不能证明桥接坏了。要抓自己发起的会话，临时在该分支加一行 `logger.info(... Jid2String(src.Chat))`，重启、发一条、抓到立刻撤掉。

⚠️ WhatsApp 官方/认证机器人账号的 JID 服务器段是 **`@bot`**（形如 `【手机号】47697@bot`），不是 `@s.whatsapp.net`，按原样填进 `chat_id`。

### 反向（WhatsApp → 飞书）零转发：先分清哪一层断

「对方回了、飞书没收到」有三种断点，日志能区分，别一上来就重启：

1. **零事件**：日志里连探针行都没有 → 事件没进驱动（连接被挤 / 对端没回 / 会话 JID 不对）。
2. **有事件、零 `on_message`** → 被 `drivers/whatsapp.py` 的 `_handle()` 分支丢掉：要么 `src.IsFromMe`（自己发的不转发，设计如此），要么消息类型落进 `else: return`。
3. **有 `on_message`** → 问题在发送侧或目标 chat_id。

定位第 2 类的固定手法（一次改完，只让用户发一条）：

- `_handle()` 开头加全量探针（`from_me / chat / sender / id`），用 `from neonize.utils.jid import Jid2String`。
- `else` 分支把**完整** `str(m)` 追加落盘——截断到几百字正好把正文切掉，等于白抓。
- 别用 `sender` 判断来源：`from_me=True` 时 sender 是自己账号的 `<lid>@lid`，`chat` 才是权威。

🔴 **认证/官方 bot 账号（`@bot` JID，如 Meta AI）的回复不是文本消息**：正文藏在 `protocolMessage{MESSAGE_EDIT}.editedMessage.richResponseMessage.unifiedResponse.data` 的 JSON 字符串里，前面还夹一串 `AI_METADATA_OPERATION`（agent 状态心跳）和 `messageContextInfo` 噪音。驱动默认的 `conversation` / `extendedTextMessage` / `imageMessage` 分支全部落空 → 静默丢弃。报文样本、抽取函数、探针补丁见 `references/whatsapp-inbound-message-types.md`；解析接入后必须端到端验一次再报「反向已通」。

### 每轮都让用户「再发一条」是失败姿势

驱动改一次就要重启一次，重启后又要用户手动发一条测试消息；连做三轮用户就会催「进度」，且每一轮都在烧他的耐心。规则：**一轮里先把本地能做的诊断全做完**（读驱动分支、跑最小监听器、落盘原始报文、离线读 db），再重启，然后一次性请用户发一条；每次汇报都要说清「哪一层已被我这边证实没问题」，别让用户替你当探针。
