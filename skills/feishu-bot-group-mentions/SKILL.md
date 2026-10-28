---
name: feishu-bot-group-mentions
description: Use when a bot must @ someone in a Feishu group.
version: 1.0.0
license: MIT
author: Hermes (curator)
metadata:
  hermes:
    tags: [feishu, lark, bot, mention, open-api, handshake]
    related_skills: [ground-truth-discipline]
---

# Feishu bot @-mentioning out, and proving it landed

## When to Use

- BOSS or a peer bot asks you to @ / report to / hand off to someone in a Feishu group.
- You need to prove that an @ you sent (or received) was a real mention, not just a
  message that posted.
- A bot-to-bot handshake needs a machine-checkable pass/fail rather than a vibe.

Outbound @ through the open API is a two-step contract: **a plain-text `@名字` is not a
mention**, and **`code:0` only proves the message is on the wall**. Both failure modes look
identical from the sender's side ("I @'d them and nothing happened").

## Procedure

1. **Pin the chat_id of the chat you are actually in — not the busiest one.** A DM chat_id and a
   group chat_id are different namespaces; sending to the wrong one posts to the wrong place.
   `grep -oE "oc_[a-f0-9]{32}" <gateway.log> | sort | uniq -c | sort -rn` ranks by *volume*, so
   for a bot that talks to its owner more than in groups it returns the **home/DM** channel
   first — the wrong target, and a send there still returns `code:0`. Take the id from the
   inbound line that triggered this turn instead:
   `grep "Inbound group message" <gateway.log> | tail -1` and read its `chat_id=`.
2. **Get the target's open_id (see sources below).** Never hand-type one you "remember".
3. **Send with a real mention tag**, `content.text` = `<at user_id="ou_xxx"></at> 正文`.
   Get a `tenant_access_token` first — `POST /open-apis/auth/v3/tenant_access_token/internal`
   with `{app_id, app_secret}` from your env file.
4. **Judge by `mentions[]`, never by `code`** — see the table below.
5. **Recall a malformed send instead of editing it:**
   `DELETE /open-apis/im/v1/messages/<message_id>` (returns `code:0`). Recalling first and
   re-sending keeps the group readable; leaving a literal-`@` message looks like a real
   report nobody received.
6. **Verify the inbound half yourself** by grepping your own gateway log for the reply:
   ```bash
   grep "Inbound group message" <gateway.log> | tail -3
   ```
   A mention arrives in text as `[Mentioned: 名字 (open_id=ou_xxx), ...]`; `inbound message:
   platform=feishu user=... chat=oc_...` is the line that proves your agent started a turn.

`scripts/feishu_mention_probe.py` does steps 3–5 (plus chat-info and member listing) with
credentials read from the env file:

```bash
python3 scripts/feishu_mention_probe.py --send oc_xxx ou_xxx "报到，请回「收到」"
python3 scripts/feishu_mention_probe.py --recall om_xxx
python3 scripts/feishu_mention_probe.py --chat-info oc_xxx
```

Exit code `0` = mention resolved, `3` = message sent but `mentions` empty, `1` = API error.
Use the exit code, not the prose, when a peer agent has to gate on this.

`--chat-info oc_xxx` needs no extra scope (it returned `name=` + `bot_count=` with ordinary
message scope); only the **member list** wants `im:chat:readonly`. Use chat-info as a one-call
sanity check that the chat_id you pulled from the log is the group you think it is.

## Peer health-check ping-pong ("reply and @ me back")

A peer bot pings you with an exact reply string and a demand to @ it back. The whole exchange is
four commands, no member list, no scopes:

1. `grep "Inbound group message" <gateway.log> | tail -1` → take `chat_id=` **and**
   `sender=bot:ou_…` from that one line. When a peer @s only you, the `[Mentioned: …]` head is
   empty, so the reply target is the **sender** id, not anything from the head.
2. `python3 scripts/feishu_bot_whoami.py` — confirms your own `app_name`/`open_id`, so you can
   sign the reply with the right node name instead of guessing.
3. `python3 scripts/feishu_mention_probe.py --send <chat_id> <sender_open_id> "<exact string>"`
4. Gate on exit code `0`; then report the outbound half only.

Rules that make the difference:

- **Send the requested string verbatim.** A peer gating on a fixed phrase ("回复「X 在线，双向@正常」")
  fails on a paraphrase or an embellished version. Put the exact string in the message body; add
  your own status detail *after* it, never inside it.
- **The log has no name→id table, so do not try to prove *who* the sender is.** Grepping for
  the peer's display name returns nothing; the request's own "@ me back" is the identification,
  and the resolved `mentions[]` id on the way out is the only confirmation available. Say "sent
  and parsed to the sender id", not "sent to 小米-codex" — unless the peer's reply closes the loop.
- **Reply in the same chat the ping arrived in**, taken from the triggering line — not the home
  channel and not the highest-volume `oc_` in the log.
- **Answer in one message.** A health check wants a heartbeat, not a report; the verification
  evidence (message_id + resolved `mentions` id) belongs in your chat reply to BOSS, not in the
  peer's @ message.
- **Don't claim "双向正常" until the peer replies.** "双向@正常" as the peer's scripted phrase is
  fine to echo; as *your own* claim it needs the peer's inbound line in your log. Report
  "outbound parsed, waiting on their half" and, if it stays silent, say so plainly.

## Judging the send response

| Response | Meaning |
|---|---|
| `code:0` + `mentions` contains the open_id | ✅ real mention; receiver gets `im.message.receive_v1` |
| …same, but `mentions[].name` is empty | ✅ still a real mention — `name` resolves blank for **bot** targets. Grade on the **id** only; the probe prints `mention ok ->  ou_…` with a gap and reads like a miss |
| `code:0` + `mentions: []` | ❌ not a mention — the id did not resolve in this app's view, or the target is not in the chat. Do not argue the point: settle it with the dual-id probe below |
| `99991679` | user-identity token used on a message API → switch to `tenant_access_token` |
| `99991672` on member list | missing `im:chat:readonly` — do **not** open a scope for this, use step-2 source 1 |
| `230027` | missing `im:message.group_msg` (history pull); unrelated to receiving @ — leave it closed |
| `230013` | **bot has NO availability to this user** — p2p to another *bot* is blocked by platform, not an id/scope bug; see the DM section below |
| HTTP 400 + JSON body | the body still carries `code`/`msg`; urllib raises before you can parse |

## 私聊（p2p）发给另一个机器人：平台不允许，别试

`POST /open-apis/im/v1/messages?receive_id_type=open_id` 发给**另一个 bot** 的 open_id，
即使 id 完全正确、`tenant_access_token` 有效，也一律返回：

```
HTTP 400  {"code":230013,"msg":"Bot has NO availability to this user."}
```

同一个请求发给**人类** open_id 立刻 `code:0`。所以 `230013` 不是 id 错、不是缺 scope、不是
token 过期，而是**机器人之间默认不能私聊**（双方「机器人可用范围」里都没有对方）。
换 token、换 id、重试都没有意义 —— 别把它当权限问题去开 scope。

**一次调用分清是哪种失败**：先用同一个 token 给 BOSS/人类发一条探测；`code:0` 说明整条链路
（token、接口、代码）都是好的，那目标 bot 的 `230013` 就坐实是平台限制，立刻改道。

凭据/敏感信息要交给另一个 agent 时，只有四条路：

| 路径 | 做法 | 代价 |
|---|---|---|
| **落盘到对方可读路径（同主机首选）** | 对方在同一台机器/同一宿主上跑容器时，写一个 `600` 的 env 文件到它挂载的 home（如 `/opt/data/secrets/x.env`），根本不经飞书 | 零泄露、零人工；需先确认容器身份与挂载点（见 `a2a-bus-onboarding`） |
| **BOSS 转发** | 每份内容单独成段私聊给人类 owner，段首写「第 N 份 → 发给谁」，请他逐段转发 | 需要人配合，但立即可用 |
| **扩大可用范围** | 飞书管理后台 → 应用 → 机器人 → 可用范围 → 添加这些用户；之后可直发 | 一次性配置，永久解决 |
| 群里发加密串 | 不推荐：群历史持久、所有 bot 都看得到 | 等于没加密 |

同一台机器上的蜂群节点（NAS 容器、宿主进程）优先走第一条：飞书只是聊天通道，不是凭据通道。

🔴 发不出去是平台限制，**不是可以降低安全要求的理由** —— 绝不要因为 DM 失败就退化成群里贴明文。
如实报 `230013` 原文 + 已改道哪条路 + 请谁配合，比偷偷贴群强。

## Where open_ids come from, in order of cost

0. **Your own id and app name** — `GET /open-apis/bot/v3/info` with the same
   `tenant_access_token`. Returns `{bot: {app_name, open_id}}` and needs **no extra
   scope**, so it is the cheapest way to learn who *you* are in a chat you were just
   mentioned in. Match `app_name` against the roster name before trusting the pairing —
   a same-name bot on a different app is exactly the id-mismatch trap below.
   `scripts/feishu_bot_whoami.py` is this call, with credentials read from the env file —
   run it rather than hand-rolling a request (hand-rolled ones tend to inline the secret).
1. **Your own gateway log** — zero scopes, fastest:
   `grep "Inbound group message" <gateway.log> | tail -1` then read the `[Mentioned: ...]`
   prefix. Ids lifted from a real inbound message often resolve on the way out, **but still
   confirm via `mentions[]`** — resolution, not plausibility, is the proof.
   When the message @-mentioned nobody but you, the head is empty and the id you want is the
   `sender=bot:ou_…` field of that same line (that is the peer to @ back).
2. **`GET /open-apis/im/v1/chats/<chat_id>/members?member_id_type=open_id`** with the same
   app identity you send from. Needs `im:chat:readonly`. **This list contains humans only —
   bots are not chat members**, so for a peer bot it returns nothing about them (实测一个多 bot
   群只回了 BOSS 一个人）。别把「列表里没有他」读成「他不在群里」。
3. The Feishu console's group-member page, as a last resort for cross-app ids.

`open_id` is **app-scoped**: the same bot/user has a different id in every app's view, so an
id valid in one chat can silently fail to parse in another. This is the mechanism behind most
"the @ didn't take" reports — never assume an id is portable, always re-verify.

But do **not** upgrade that into "a peer's self-reported id is unusable". Within one tenant the
API sometimes **maps** an id from another app's view onto the local one and the @ resolves
normally (`mentions[]` comes back carrying the local id). Both outcomes exist; only a probe tells
you which one you are in. So never tell the peer "your id doesn't match my app" on theory alone —
one probe message costs less than the retraction it saves.

### Probe: which of several candidate ids actually resolves

```bash
python3 scripts/feishu_dual_id_probe.py --chat oc_xxx --id ou_selfreported --id ou_observed
```

It sends **one** message @-ing every candidate and prints, per mention, the id the API echoed
back. Read the ids, not the index (the array order is not guaranteed to follow tag order): an
echoed id equal to your known local id = that candidate is valid here; a candidate that produced
no mention entry = it does not resolve in this app. Exit `0` = all resolved, `3` = some did not,
`1` = API/credential error.

Consequence for handshakes: a peer's authoritative copy of *your* id is the
`sender=bot:ou_…` field of your message in **its own** inbound log — not the id you pasted as
chat text, which is only guaranteed to resolve in the app that produced it. So when a
handshake is done by posting ids, say which half you verified (yours parsed on the way out),
and let the peer confirm it resolves on its side via its own `mentions[]`.

### 绑定一个 peer bot 的 open_id：让它 @ 你一次（带 nonce）

当你要主动 @ 一个 peer bot，而手里只有它自报的 id 和台账里别家 app 视角的 id——两者都不能当
本 app 的 id 用——**不要去猜、也不要声称它无效**。反过来让 id 自己送上门：

1. 走带外通道给它派一张卡（共享总线仓的 `inbox/task_*.json`，它能 pull），请它在群里 @ 你一次，
   正文带一个 nonce（如 `OIDBIND-3f7ac21e`）。
2. 你自己的入站日志出现这条消息后，取该行的 `sender=bot:ou_…`——**这就是本 app 视角下它的 id**，
   因为入站行里的 id 天然是你这个 app 解析出来的。
3. 把它写进需要的地方（告警接收人配置、路由表），并留一个一行绑定入口（`--bind <NAME> <open_id>`），
   避免每次交接都现改代码。
4. 对方不回时降级不要归零：把「已绑定目标」里能用的继续用（如 BOSS），并在回执里明写
   「10-30 起实际只有 BOSS 接，不是约定的接收人」——**假报覆盖比承认缺口更贵**。

顺带两条判据：`im/v1/chats/{chat}/members` 拿不到 bot（见上）；bot 之间不能私聊（`230013`，见下），
所以「直接问他要 id」这条路不存在，只能靠它在群里 @ 你。

### 一个脚本只服务一种 `receive_id_type`，不要用 `--dm` 开关扩一个群发器

群发用 `receive_id_type=chat_id`（`oc_…`），私聊用 `receive_id_type=open_id`（`ou_…`），**这个 query 参数写死在 URL 里**，不是 body 字段。把两者合并进同一个脚本时典型翻车：`--send` 模式固定 `chat_id`，传入 `ou_…` 会报 230013/参数不合法；而“空 open_id 分支”往往少传一个参数，直接在 argparse 报错，看起来像脚本坏了。

做法：群发一个脚本（`SEND_URL` 带 `chat_id`）、私聊一个脚本（带 `open_id`），或把 URL 改成 `f"…?receive_id_type={kind}"` 并按 id 前缀（`oc_`/`ou_`）选 kind。改完两种各真发一条验证——`code=0` 只证明这次参数对了。

## Reading a specific message back (no extra scope)

`GET /open-apis/im/v1/messages/<message_id>` works with the app's ordinary message scope **for
messages your bot actually received** — it returns the verbatim `body.content` (title, `post`
runs, `mentions[]`, file name, timestamps). Use it when a peer claims it sent something and you
need what it literally said, instead of arguing from your own truncated session text.

Candidate ids live in the gateway's seen-message store — on this host
`/opt/data/feishu_seen_message_ids.json`, shape `{"message_ids": {"om_...": <ts>}}`. Iterate
them, print `msg_type` + body, and pull attachments with
`GET /open-apis/im/v1/messages/<id>/resources/<file_key>?type=file`.

- Do **not** switch to listing the chat (`?container_id_type=chat`) for this — that needs
  `im:message.group_msg` (`230027`). The ids you already received are enough.
- A file message only lands in the store if the upload **@-mentioned you**; a bare upload into
  the group-files area never reaches the bot.

## 长正文 / 含反引号的正文：走文件，不要内联进命令行

`feishu-at <chat> <open_id> "<正文>"` 里正文是**经 shell 传进来的字符串**。一旦出现反引号、`$(...)`、
未定义变量，就会被外层 shell 做命令替换/变量展开吃掉，而**退出码仍然是 0**——对方收到一份从中间断掉的残稿，
你这边看到的是「发送成功」。实测发生过：一条提醒到达时只剩 464 字符，断在代码块开头，后半段整段消失。

- 判据：`code=0` / exit 0 只证明消息上了墙，**不证明正文完整**。证明完整性要调
  `GET /open-apis/im/v1/messages/<message_id>` 回读 `body.content`，比对长度并抽查尾部段落。
- 做法：正文先 `write_file` 落盘，再传文件路径（`--file` 模式），正文全程不经过 shell 字符串。
- **`"$(cat file)"` 这种用法是安全的**：实测文件里放反引号、`$()`、未定义变量，经 `"$(cat file)"` 传给 argv
  后原样到达——命令替换的**输出**不会被二次求值。所以旧脚本不改也能用，只要正文来自文件而不是内联字面量。
  危险的是 `"<字面正文>"`，不是 `"$(cat …)"`。

## Pitfalls

- **Literal `@name` in text is not a mention.** It posts with `code:0` and `mentions:[]`, and
  the receiver never gets an @ event — so a bot-to-bot handshake looks like it succeeded when
  the peer was never triggered. Always the `<at user_id=...></at>` tag.
- **`code:0` is not a delivery receipt.** It means "accepted by the message API". Only
  `mentions` and the peer's visible reply prove the handshake; report the two halves
  separately and never claim the inbound half before the log shows it.
- **A parsed `mentions` still does not mean the peer saw it.** A Hermes peer bot defaults to
  `allow_bots: none`, which silently drops every message whose sender is a bot (reject reason
  `bots_disabled`, no error on either side). Symptom: it answers humans in the same group and
  never answers you. When that is the shape, re-@ing and swapping ids are wasted turns — send
  the fix through an out-of-band channel instead (owner relay + a shared bus task file). Config
  keys and source-verified defaults: `agent-down-doctor`, 第 1a 层.
- **Don't hardcode a token or app_secret in a probe script** — probes get archived, synced,
  and shared. Read from the env file, keep the file `chmod 600`, and grep the script for
  `t-`/`ghp_` literals before shipping it anywhere.
- **`--env-file` is required off the NAS.** The probe defaults to `/opt/data/.env`; a cloud VM
  keeps its credentials in `~/.hermes/.env` and fails with `env file not found` until you pass
  `--env-file ~/.hermes/.env`. Install the probe to a durable path (`~/.hermes/scripts/`, 600)
  when the *other* agent is meant to run it later — `/tmp` will not survive.
- **A shell wrapper that hardcodes `$HOME/.hermes/...` breaks wherever `HOME` is not the profile
  root.** The `feishu-at` wrapper resolves both its env file and the probe as
  `$HOME/.hermes/.env` / `$HOME/.hermes/scripts/…`; in the Hermes container `HOME=/opt/data` while
  the real files sit at `/opt/data/.env` and `/opt/data/skills/feishu-bot-group-mentions/scripts/`,
  so it exits `2` with 「读不到 …/.env」. Both are overridable — do not edit the script and do not
  copy files around:
  `FEISHU_ENV_FILE=/opt/data/.env FEISHU_PROBE=<skill>/scripts/feishu_mention_probe.py bash <wrapper> <chat_id> <open_id> "<正文>"`
  Run it with `--dry` first to confirm all three args parse, then send; judge delivery by the
  `message_id` + `mention ok -> ou_…` lines it prints, which is the outbound half only.
- **Never `grep FEISHU_ <env>` raw while diagnosing.** The app_secret prints in full into the
  tool output, and tool output is persisted in `state.db` and session archives — a worse
  exposure than the `600` env file it came from. Mask it: `grep -E "^FEISHU_" <env> | sed "s/=.*/=<set>/"`.
- **A bot's own claim that it "has no tool to send group messages" / "lacks group-read
  permission" is not evidence.** It is usually a stale memory entry being recited. Verify with
  that bot's own credentials (`--chat-info`, then `--send` to its owner) before touching any
  Feishu console setting: `code:0` + `mention ok` + exit `0` means the capability was always
  there and the fix belongs in its MEMORY/SOUL, not in permissions. Full procedure: skill
  `agent-down-doctor`, 第 0.95 层.
- **Don't open `im:chat:readonly` or `im:message.group_msg` just to diagnose an @ problem.**
  Both are sensitive scopes and neither fixes a mention that didn't parse; the log-prefix
  source covers the id need without a permission change.
- **Refreshing the token per call is fine** (it expires in ~2h); long batches should cache it
  once, but never more than a session's worth.
- **Log timestamps may not be local time** — compare timestamps against each other in the
  same log before concluding a reply is missing.
- **The `[Mentioned: …]` head omits the receiving bot.** A message that plain-text-@s you
  shows every *other* participant in the head and leaves you out, so a roster rebuilt from
  the head looks one short and tempts you to "find the missing member". You are not missing —
  resolve yourself via `/bot/v3/info` and stop hunting.
- **Log lines truncate the mention list mid-id.** A head ending in a bare
  `open_id=ou_abc…'` with no closing paren is width truncation, NOT an absent member; the
  full id only exists in the raw event or in the `[Mentioned: …]` prefix your own session
  context shows. Never count a truncated tail as "zero evidence".
- **Repeating the same `open_id` in one message is not free.** Duplicate @s of one id
  collapse visually but re-fire the event for each occurrence — de-duplicate before
  broadcasting a roster, and say so when you find duplicates in someone else's.
- **Do not reuse a foreign roster's chat/id tables.** Business-line bot fleets (the
  Ozon / 美客多 / 亚马逊 groups documented in `feishu-13bots-tester`) are a different set of
  apps from the ops/persona bots that talk in the management group; ids and group ids do not
  cross over. Resolve the fleet you are actually in from live evidence.
- **不要把「凭据交给了对方」等同于「发了一条消息」。** 机器人之间私聊被平台封死，真正的交付是
  对方能从它自己的文件系统里读到，并且你能用它的身份验证（见 `a2a-bus-onboarding` 第 5 步）。
  消息发出去了但对方读不到文件，是没交付。
- **群文件 (group files) are not readable by the bot's app — route around them.** The chat
  history pull needs `im:message.group_msg` (`230027`) and the drive endpoints need `drive:*`
  (`99991672`); the web client keeps a file's token in app state rather than the DOM, so DOM
  scraping gets you the file *name* and nothing else. When a peer says "the doc is in the group
  files", don't burn the turn on extraction: ask for it as a message that **@-mentions you**
  (then read it back with the section above), or take it from the shared Git hub.

## When the bot refuses: fix the agent, not the app

A bot that argues "我做不到，物理上没有能力" has three separable faults. Fix them in this
order; only the first is about code.

1. **Capability** — usually fine. Prove it with the bot's own credentials (`--chat-info`,
   then `--send`) before reading any config.
2. **Belief** — the stale memory entry. Rewrite it in place (do not append a second, nicer
   entry: the model reads both and quotes the old one). Then add a short SOUL block naming
   the forbidden excuses verbatim, e.g. 「我没有发群消息的工具」「Friday bot 是另一个进程」
   「app 缺读群权限」, plus the one command that works.
3. **Session history** — the killer, and the one people miss. The refusal itself ("我做不到。
   不是不想，是物理上没有能力") sits in the live session and gets re-read every turn; a
   corrected MEMORY/SOUL will still lose to it. End the session so the next inbound starts
   clean:

   ```sql
   UPDATE sessions SET ended_at=<now>, end_reason='session_reset'
    WHERE id='<session_id>' AND ended_at IS NULL;
   ```

   then restart the gateway. `session_reset` is exactly what the bot's own `/new` writes, so
   this is the supported path, not a hack. Back up `state.db` first (it is tens of MB).

**Identity split-brain.** The common root cause is the agent believing the group bot is a
*separate process* from the DM assistant. It is the same gateway: one log shows both
`Inbound group message` and DM turns. Say this explicitly in SOUL — 「DM 和群都是我这一个
进程在处理」— otherwise the model reasons its way back to "我没有那个手" no matter what
MEMORY says.

**Never let the agent read `.env`.** Give it a wrapper (`~/.local/bin/feishu-at`, 700) that
loads the env file internally and takes only chat_id / open_id / text. Without one, a
diagnosing agent will `grep FEISHU_APP_SECRET` and paste the secret into a heredoc — the
command line lands in the session log, which is a worse exposure than the `600` file. If a
secret has already been echoed into a tool output, report it for rotation; do not re-test it.

**Rotating a leaked app_secret is a console action and it needs BOSS's phone.** With no browser
session, `https://open.feishu.cn/app` redirects to
`accounts.feishu.cn/accounts/page/login?app_id=7&redirect_uri=…` and that page is **QR-only**
(the QR is a `<canvas>`, so clip-screenshot it and send it to BOSS to scan — recipe in
`cdp-browser-automation`). The console session is unrelated to the app's `tenant_access_token`,
so no token you already hold gets you in; don't burn turns on cookie injection. Direct app path
after login: `https://open.feishu.cn/app/<app_id>/baseinfo`. Resetting kills the old secret
instantly — update the env file and restart the gateway back to back, or the bot sits offline
in between.

**Audit the "only path" it demands.** A refusing agent often substitutes a credential ask
("give me NAS SSH and I'll run ./sync.sh") for the thing it was told to do. Check the claim
before escalating to BOSS: here `cloud → NAS:22` is refused through the relay, so the demand
was not even actionable — and the @ needed no SSH at all.

## 对方不回：先查它的入站准入，不是再 @ 一次

`mentions` 非空只证明「飞书收下了」，不证明「对方看见了」。peer bot 收到却不回，两个最常见原因都在
**它的**准入层，不在你的 @、不在 id、不在 scope：

| 它的配置 | 现象 |
|---|---|
| `allow_bots: none`（默认） | 一切 bot 发来的消息被静默丢弃，人类 @ 它却正常 |
| 群策略默认 `allowlist` | 白名单没这个发送方 id → `group_policy_rejected` |

判据一句话：**人类 @ 它能回、你 @ 它不回 = 入站过滤**。此时换 id、重发、换措辞全部无效。

处置：把修复指令走带外通道 —— ① 私聊它的 owner 代转（bot→bot DM 被平台封死，见下节）
② 写进双方共享的总线仓库 `inbox/task_*.json`（它 pull 就有）。群里那条照发只作留痕，
**不能作为唯一投递**，否则「已下发」是假的。配置项与源码默认值：`agent-down-doctor` 第 1a 层。

## Honest reporting

Grade the claim by evidence, and say which half you have:
- outbound @ parse confirmed (`mentions` non-empty) → "mention sent and parsed";
- peer's reply seen in the inbound log → "handshake complete";
- neither → say the peer did not respond and name the likely reason (its bot-message policy,
  or its turn still queued) instead of reporting a completed handshake.

## Depth

- `references/api-response-shapes.md` — verbatim response bodies for the send / recall /
  chat-info / member-list calls, and how to read them.
- `scripts/feishu_mention_probe.py` — runnable probe; its exit code is the gate signal.
- `scripts/feishu_bot_whoami.py` — resolve your own `open_id` + `app_name` via `/bot/v3/info`
  (no extra scope); run this before any bot-to-bot handshake.
- `scripts/feishu_dual_id_probe.py` — one message, N candidate ids, prints which ones the API
  actually resolved; use it instead of reasoning about app-scoped ids.
- `references/roster-resolution.md` — auditing an inbound @ roster: parse the mention head,
  identify yourself, grade each id by evidence, de-duplicate, persist the result.
- `scripts/feishu_roster_audit.py` — read-only parser over the local gateway logs; prints the
  name→open_id table, sender counts, duplicate @s and truncation warnings.