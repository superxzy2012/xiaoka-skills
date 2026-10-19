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
| `code:0` + `mentions: []` | ❌ not a mention — open_id is from another app's view, or target is not in the chat |
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

凭据/敏感信息要交给另一个 agent 时，只有三条路：

| 路径 | 做法 | 代价 |
|---|---|---|
| **BOSS 转发（默认）** | 每份内容单独成段私聊给人类 owner，段首写「第 N 份 → 发给谁」，请他逐段转发 | 需要人配合，但立即可用 |
| **扩大可用范围** | 飞书管理后台 → 应用 → 机器人 → 可用范围 → 添加这些用户；之后可直发 | 一次性配置，永久解决 |
| 群里发加密串 | 不推荐：群历史持久、所有 bot 都看得到 | 等于没加密 |

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
   app identity you send from. Needs `im:chat:readonly`.
3. The Feishu console's group-member page, as a last resort for cross-app ids.

`open_id` is **app-scoped**: the same bot/user has a different id in every app's view, so an
id valid in one chat can silently fail to parse in another. This is the mechanism behind most
"the @ didn't take" reports — never assume an id is portable, always re-verify.

Consequence for handshakes: a peer's authoritative copy of *your* id is the
`sender=bot:ou_…` field of your message in **its own** inbound log — not the id you pasted as
chat text, which is only guaranteed to resolve in the app that produced it. So when a
handshake is done by posting ids, say which half you verified (yours parsed on the way out),
and let the peer confirm it resolves on its side via its own `mentions[]`.

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

## Pitfalls

- **Literal `@name` in text is not a mention.** It posts with `code:0` and `mentions:[]`, and
  the receiver never gets an @ event — so a bot-to-bot handshake looks like it succeeded when
  the peer was never triggered. Always the `<at user_id=...></at>` tag.
- **`code:0` is not a delivery receipt.** It means "accepted by the message API". Only
  `mentions` and the peer's visible reply prove the handshake; report the two halves
  separately and never claim the inbound half before the log shows it.
- **Don't hardcode a token or app_secret in a probe script** — probes get archived, synced,
  and shared. Read from the env file, keep the file `chmod 600`, and grep the script for
  `t-`/`ghp_` literals before shipping it anywhere.
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
- **群文件 (group files) are not readable by the bot's app — route around them.** The chat
  history pull needs `im:message.group_msg` (`230027`) and the drive endpoints need `drive:*`
  (`99991672`); the web client keeps a file's token in app state rather than the DOM, so DOM
  scraping gets you the file *name* and nothing else. When a peer says "the doc is in the group
  files", don't burn the turn on extraction: ask for it as a message that **@-mentions you**
  (then read it back with the section above), or take it from the shared Git hub.

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
- `references/roster-resolution.md` — auditing an inbound @ roster: parse the mention head,
  identify yourself, grade each id by evidence, de-duplicate, persist the result.
- `scripts/feishu_roster_audit.py` — read-only parser over the local gateway logs; prints the
  name→open_id table, sender counts, duplicate @s and truncation warnings.