# Location & auth ceilings

What a client-side override can and cannot move. Read this before spending turns on a
location-gated flow.

## Two different layers

| Layer | Movable by the client? | Symptom when wrong |
|---|---|---|
| Browser geolocation (`navigator.geolocation`) | Yes — `ctx.grant_permissions(["geolocation"])` + `ctx.set_geolocation({...})` | Page shows "enable location", merchant list stays at the cached/city default |
| Server-derived location (account's saved delivery address) | **No** | List keeps showing the *old* city's shops and distances after you "changed" the address |

The failure mode that burns time: you pick a new address in the UI, the selection *appears* to
stick, but the shop list still shows the previous city. That means the list is server-derived.
Re-injecting GPS will not change it — the server has no idea the browser moved.

## Proving a guest session (do this before debugging location)

Cookie names lie. A logged-out browser still holds `userId`, `token`, `uuid`, `_lxsdk_cuid`.
The only reliable check is an endpoint behind the login:

```python
# 1. watch which endpoints the page itself calls
pg.on("response", lambda r: holder.put(r.url, r.json() if "json" in (r.headers.get("content-type") or "") else None))
# 2. trigger the action that needs auth (pick an address, open "my account")
# 3. read the status code
```

`{"code": 401, "msg": "<...>login..."}` = guest, regardless of how many cookies exist.
Only after a **200 with real data** from an authed endpoint can you claim a session.

## Order of escalation

1. Can the task be done with a *different* entry point that does not need the account's
   default address? (search-by-keyword often works as a guest)
2. If the user is willing: have them complete the one login in their own window — no
   credential ever passes through the conversation — then re-export cookies.
3. If neither works, say so and offer the alternative (user completes the final step
   themselves, or the task moves to a different channel). Do not loop on injections.

## Cleanup when abandoning a flow

If the user drops a capability, delete the script and the exported cookies, and leave one
line in the relevant skill recording *which probe failed* so the dead end is not re-explored.
Also decide explicitly whether the user's real input (e.g. a delivery address) is still worth
keeping — that is usually yes, it is just the platform that was dropped.
