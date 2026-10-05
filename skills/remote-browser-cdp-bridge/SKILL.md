---
name: remote-browser-cdp-bridge
description: Drive a remote Chromium's existing login state over CDP.
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [cdp, playwright, browser, cookies, auth, automation]
    related_skills: [agent-browser-core, video-ingest-pipeline]
---

# 远程浏览器会话桥接（CDP）

Drive a Chromium instance that lives on **another machine** and already holds the user's
login state, instead of trying to log in headlessly from a server IP.

Use when: a site blocks a datacenter IP, the user has already logged in on their desktop
browser, or a task needs a session (cookie jar) that only a real browser has.

## When to Use
- Site returns a captcha/blank/interstitial only for *your* server's IP, but works on the user's laptop.
- The user says "my Chrome is already logged in" / "reuse my browser".
- You need cookies for a CLI tool (yt-dlp, curl) that cannot run a browser.

## Procedure

1. **Confirm the bridge is up before anything else.**
   `curl -s http://<host>:<port>/json/version` must return `webSocketDebuggerUrl`.
   If this fails, nothing below works — fix the bridge first.

   Diagnose *before* touching the firewall, because the two failures look identical to the user:
   - `Connection refused` → nothing is listening on that port. Add/fix the relay; a firewall
     rule will not help.
   - Connect succeeds but read hangs / times out → the port IS listening, something upstream is
     dropping packets. Now a firewall rule is the fix.

   When the debug port binds to loopback only, expose it with a userspace TCP relay rather than
   asking the user to relaunch the browser with a different bind flag — current Chromium
   releases ignore `--remote-debugging-address` and bind `127.0.0.1` regardless. See
   `references/loopback-only-devtools-exposure.md` for the Windows relay recipe.

   Verify the bind from the host, not from the browser's own machine. `curl http://127.0.0.1:PORT`
   succeeding locally proves nothing about reachability — it is the loopback path working. The
   only verdict that matters is the listener's `LocalAddress`: `127.0.0.1` means the port is
   unreachable from anywhere else no matter what firewall rules exist, and `0.0.0.0` means the
   relay chain is live. Check it and relay in one command, not in separate rounds:

   ```powershell
   Get-NetTCPConnection -LocalPort 9223 -State Listen | Select-Object LocalAddress
   # 127.0.0.1 -> add the relay; 0.0.0.0 -> relay + firewall already in place
   netsh interface portproxy add v4tov4 listenaddress=0.0.0.0 listenport=9224 connectaddress=127.0.0.1 connectport=9223
   New-NetFirewallRule -DisplayName CDP-fwd -Direction Inbound -Action Allow -Protocol TCP -LocalPort 9224 -Profile Any
   ```

   Don't re-try the bind flag with different quoting, launchers, or flags after the first
   `127.0.0.1` verdict. It is a browser-version behaviour, not a syntax problem — the same
   command through PowerShell's array form, `Start-Process -ArgumentList`, and `cmd /c start`
   all produce loopback-only. Switch to the relay.

2. **Connect with playwright, not the `browser` tool.**
   ```python
   b = p.chromium.connect_over_cdp("http://<host>:<port>")
   ctx = b.contexts[0]          # pages live on the CONTEXT
   pg = ctx.new_page()
   ```
   **`Browser` has no `.pages` attribute over CDP** — use `b.contexts[0].pages`. Getting this
   wrong throws `AttributeError` and looks like a connection failure.

3. **Read page content with playwright's own APIs, not JS eval.**
   `pg.inner_text("body")` and `pg.evaluate(...)` are reliable. A wrapper's `js()` helper may
   return `{}` for a perfectly good page (serialization round-trip drops the value) — that is a
   broken readout, not an empty page. Verify with a second signal (URL + title + text length)
   before concluding the page is blank.

4. **Verify auth with a real authenticated request, never with cookie presence.**
   Cookie names are not proof: a logged-out browser still carries `userId`/`token`/`uuid`
   guest cookies. Call an endpoint that requires auth and read the status code
   (`{"code":401,"msg":"..."}` = guest). Pick any endpoint behind the login.

   `document.cookie` is **not** a valid source for this verdict. Session cookies on major sites
   are `HttpOnly`, so a fully logged-in browser reads back a plausible-looking short cookie
   string with the session name missing — which reads as "not logged in". Use CDP
   `Storage.getCookies` (see below) or playwright's `context.cookies()`, which include them.

5. **Export cookies once, then work headlessly.**
   Write both formats: `context.cookies()` → JSON (replayable via playwright) and Netscape
   `.txt` (for yt-dlp/curl). Re-export whenever the user re-logs-in.

6. **If the site is location-gated, know when to stop.**
   Server-side location (computed from the account's default address) cannot be moved by
   injecting browser geolocation. See `references/location-and-auth-ceilings.md`.

## Pitfalls

- **`Storage.getCookies` rejects `browserContextId: null`.** Passing the parameter at all —
  even as `None` — returns `-32602 Invalid parameters`. Send `{}` and filter by domain client-side.
- **Guessing a cookie's *name* to decide auth produces a false negative.** Don't test for
  `uid_tt`/`SESSDATA`/`sessionid` by memory — dump the actual names and match them against the
  full `Storage.getCookies` list, and key off presence of a value plus the cookie count moving.
  A site can rename these and a browser can be fully authenticated while every name you remember
  is absent. A short cookie count that *grows* after the user logs in (e.g. 1030 → 4251 bytes) is
  the real signal that login landed; the name check alone produced a wrong "not logged in".
- **A config value pointing at a stale address is worse than no config.** An endpoint written
  months ago for a DHCP-assigned IP looks correct and fails as `refused`/`no route`, which reads
  as "bridge is down" rather than "address moved". Verify every configured host:port still
  resolves before blaming the bridge, and re-derive it by probing the candidate addresses
  directly. Back the file up before editing it.
- **A short `document.cookie` is not evidence of logout.** `HttpOnly` session cookies are
  invisible to JS by design; reading login state from JS produces a false negative on exactly
  the sites you most need (video platforms, social). See step 4.
- **Copying a browser profile does not copy a usable login state.** Cookies in a copied
  `--user-data-dir` may be bound to the original install's encryption key, so the clone boots
  logged out. Have the user sign in once *inside the dedicated automation profile*; that login
  then persists across restarts. Do not loop on re-copying the profile.
- **Guest vs real login**: a browser can hold dozens of cookies and still be a guest. Always probe an authed endpoint before promising a flow works.
- **A stored "method X is blocked" conclusion goes stale on any browser restart.** Re-probe `Runtime.evaluate` / `Page.navigate` / in-page `fetch` on a fresh tab before telling the user a task needs their hands — refused navigation and dead API calls both get re-enabled by a restart or policy reload.
- **Never invent ports or paths — scan and fingerprint.** A `200` on a guessed path is usually an SPA catch-all; read status *and* content-type together. The front-end bundle is the API map for panels that ship no docs. Confirm a port serves what you assume — a port you assumed was the vendor panel may be the user's own side project.
- **A panel that bounces to `#/login/…` loads its privileged routes only after auth.** The bundle you can fetch while logged out holds just the public API surface; absence of a container/service endpoint proves nothing about whether one exists. See `references/cross-host-admin-grants.md` for the boundary sweep and the one-step handoff.
- **`location.hash` ending in `#/login/` is the verdict, not `localStorage`.** An `appKey` in storage is written before login finishes and reads like a live session.
- **Key material handed to a user must come from the private key.** A `known_hosts` line is indistinguishable from a public key and pastes cleanly while authorizing nothing.
- **`connect_over_cdp` `.pages` AttributeError**: pages are on `b.contexts[0]`, not the Browser.
- **Playwright browser install location**: if the download fails with EACCES on a dirlock, the
  env var `PLAYWRIGHT_BROWSERS_PATH` points at a root-owned dir — override it to a writable path.
- **The bridge depends on the other host staying up.** State this as a constraint, not a bug.
- **Never type credentials.** Login walls are the user's to clear in their own window; the
  session is then reused over CDP without the secret ever entering the conversation.

## Depth
- `references/loopback-only-devtools-exposure.md` — relaying a loopback-bound debug port to the
  LAN (Windows `netsh portproxy` + firewall), and the bind-address check that proves it worked.
- `scripts/cdp_client.py` — stdlib-plus-`websocket-client` CDP class: own-tab discipline,
  id-matched request loop, `eval_js` / `cookies` / `cookie_header`. Import it instead of
  hand-writing the request loop.
- `references/location-and-auth-ceilings.md` — what client-side GPS overrides can and cannot fix, and how to prove a guest session.
- `references/cookie-export.md` — dual-format export recipe (playwright JSON + Netscape for CLI tools).
- `references/raw-cdp-and-target-recon.md` — raw CDP without playwright (own-tab discipline, `suppress_origin`, id-matching request loop), probing an unauthenticated vendor panel for real ports/API prefix, and packaging a handoff command.
- `references/cross-host-admin-grants.md` — sweeping every privilege channel once, fingerprinting vendor panel ports, and shipping a verified one-step SSH pubkey handoff.
