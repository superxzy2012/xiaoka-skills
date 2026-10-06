# Resolving an @ roster (who is who in a group)

Use when a message arrives with a long `[Mentioned: …]` list — typically a broadcast to every
agent in a management group — and you need to say something true about the participants:
who replied, who is a bot, whose id is only claimed by one message, and what to persist.

## Procedure

1. **Read the head from the raw event, not from memory.** The full, untruncated
   `[Mentioned: 名字 (open_id=ou_xxx), …]` prefix is in the inbound event text your own
   session context shows. Gateway log lines render the same head at a fixed width and cut it
   mid-id; treat a trailing `open_id=ou_…'` with no closing paren as truncation, never as an
   absent member.
2. **Identify yourself.** `GET /open-apis/bot/v3/info` (same `tenant_access_token`, no extra
   scope) returns your own `app_name` + `open_id`. The mention head **omits the receiving
   bot**, so the head alone always looks one short. Fill yourself in from this call instead
   of hunting the missing member.
3. **Grade every other id by evidence**, cheapest first:
   - `sender=bot:ou_…` / `sender=user:ou_…` lines in the logs → that participant has
     actually spoken here.
   - repeated appearance in a mention head across several messages → stable participant.
   - exactly one appearance, in a truncated head → **single-message claim, unproven.**
   Say so in those words. Do not present "I have never seen it" as "it does not exist" —
     a quiet bot is indistinguishable from an id pasted in by hand.
4. **De-duplicate.** The same id repeated in one message re-fires the event; the UI collapses
   it. Count by `open_id`, not by mention position, and report duplicates as a defect in the
   broadcaster's message.
5. **Note members who were NOT mentioned.** Compare the parsed head against the sender lines
   for the same chat: a participant who spoke earlier but is absent from the current roster
   was dropped on purpose (or by an app-scoped id mismatch) — worth one line.
6. **Persist what you verified** to a roster file (name → open_id → what proved it: spoke /
   mentioned-N× / single claim / self). Re-derive from live evidence next time; treat the file
   as a cache with a "verified by" column, never as an authority.

## Two fleets do not share ids

`open_id` is app-scoped. A business-line fleet (the Ozon / 美客多 / 亚马逊 groups with their
own chat-id table in `feishu-13bots-tester`) and the ops/persona bots that talk in the
management group are different apps: ids, group ids, and even the number of bots differ. Do
not carry one fleet's roster or chat table into the other; resolve the fleet you are in.

## Reporting shape

A table works best for rosters: name, id (truncate to `ou_xxxxxxxx…suffix`), participant kind
(human / bot), and the evidence grade. Then a short list of the actual anomalies
(duplicates, unproven ids, dropped members) and one concrete next step ("say 核实名册 and I
will probe every id outbound and judge by `mentions[]`"). Do not open with a narrative of how
you read the logs.