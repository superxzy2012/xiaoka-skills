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

1. **Pin the chat_id.** A DM chat_id and a group chat_id are different namespaces; sending to
   the wrong one posts to the wrong place. `grep -oE "oc_[a-f0-9]{32}" <gateway.log> | sort | uniq -c | sort -rn`
   shows which chat this bot actually talks in.
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

## Judging the send response

| Response | Meaning |
|---|---|
| `code:0` + `mentions` contains the open_id | ✅ real mention; receiver gets `im.message.receive_v1` |
| `code:0` + `mentions: []` | ❌ not a mention — open_id is from another app's view, or target is not in the chat |
| `99991679` | user-identity token used on a message API → switch to `tenant_access_token` |
| `99991672` on member list | missing `im:chat:readonly` — do **not** open a scope for this, use step-2 source 1 |
| `230027` | missing `im:message.group_msg` (history pull); unrelated to receiving @ — leave it closed |
| HTTP 400 + JSON body | the body still carries `code`/`msg`; read it, urllib raises before you can parse |

## Where open_ids come from, in order of cost

1. **Your own gateway log** — zero scopes, fastest:
   `grep "Inbound group message" <gateway.log> | tail -1` then read the `[Mentioned: ...]`
   prefix. Ids lifted from a real inbound message often resolve on the way out, **but still
   confirm via `mentions[]`** — resolution, not plausibility, is the proof.
2. **`GET /open-apis/im/v1/chats/<chat_id>/members?member_id_type=open_id`** with the same
   app identity you send from. Needs `im:chat:readonly`.
3. The Feishu console's group-member page, as a last resort for cross-app ids.

`open_id` is **app-scoped**: the same bot/user has a different id in every app's view, so an
id valid in one chat can silently fail to parse in another. This is the mechanism behind most
"the @ didn't take" reports — never assume an id is portable, always re-verify.

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