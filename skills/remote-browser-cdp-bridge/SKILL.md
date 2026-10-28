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

   Diagnose *before* touching the firewall, because the failures look identical to the user:
   - `Connection refused` → nothing is listening on that port. Add/fix the relay; a firewall
     rule will not help.
   - `Connection reset by peer` → a relay/portproxy rule is listening but has **no live CDP
     service behind it** (the browser closed, or its debug port never came up). The relay is
     not the problem; the browser process is. Confirm from the browser host that the backing port
     actually has a listener — a rule pointing at a dead port is the signature.
   - Connect succeeds but read hangs / times out → the port IS listening, something upstream is
     dropping packets. Now a firewall rule is the fix.

   Verify the backing listener from the browser host, not from your own side. Two hop-checks
   tell you which of the two ends broke: your side (`curl` to the relay) and the browser host's
   own `netstat -ano | findstr LISTENING` for *both* the relay and backing ports. If the relay
   port is listening and the backing port is not, the browser needs restarting — no firewall or
   relay edit will fix that.

   When the debug port binds to loopback only, expose it with a userspace TCP relay rather than
   asking the user to relaunch the browser with a different bind flag — current Chromium
   releases ignore `--remote-debugging-address` and bind `127.0.0.1` regardless. See
   `references/loopback-only-devtools-exposure.md` for the Windows relay recipe. If the automation
   account on that host is **not** an administrator, skip the relay and use `ssh -L
   <local>:127.0.0.1:<port>` (same reference): `portproxy` and firewall rules both need elevation.

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
- **`__Host-` prefixed cookies cannot go through `context.add_cookies()`.** Passing `domain`
  fails with `Invalid cookie fields`; passing `url` fails with `Cookie should have either url or
  path`. Both are the same cause: `__Host-` requires `secure`, `path=/`, and **no** domain, which
  playwright's cookie validator does not model. Inject those through a **page-level** CDP session
  instead:
  ```python
  ctx.add_cookies([c for c in cookies if not c["name"].startswith("__Host-")])
  pg = ctx.new_page()
  cdp = ctx.new_cdp_session(pg)          # page-level; browser-level has no Network domain
  cdp.send("Network.setCookie", {"name": n, "value": v, "url": "https://<host>/",
                                 "secure": True, "sameSite": "Lax"})
  cdp.detach()
  ```
  `b.new_browser_cdp_session()` rejects the same call with `'Network.setCookie' wasn't found` —
  Network is a target-domain API, so the session has to ride a page. Get the split wrong and you
  silently drop the session cookie while the page still renders: the site shows a guest/empty
  shell, which reads as "login expired" rather than "one cookie never landed".
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
- **Guest vs real login**: a browser can hold dozens of cookies and still be a guest. Always probe an authed endpoint before promising a flow works. A text scan is the worst form of this check: searching the page for `Sign In`/`Dashboard` returns a logged-in verdict on a **localized guest page** (`登录`), so classify by an authed endpoint's status code, never by English keywords.
- **When a page read comes back empty, escalate to a trivially-true probe before blaming your selector.** `document.title` and `location.href` returning `None`/empty while your careful DOM query also returns nothing means the **session is dead**, not that the selector is wrong. Chasing selectors against a dead session burns the whole loop — one navigation per item at 10s each turns a diagnosable outage into a silent all-items-failed batch. Probe once at script start and exit immediately with a clear message, so the failure costs seconds instead of the run.
- **`AttributeError: module has no attribute 'goto'` is a wrong API call, not a dead bridge.** Read the helper's actual surface before using it — helpers usually expose methods on an instance (`CDP().goto(...)`), so a module-level `cdp.goto(...)` fails with an error that looks like a connectivity problem. Confirm with the same trivially-true probe: if `document.title` works, the bridge is fine and the bug is in your call. Tell these two apart early, because "the bridge is down" sends the user to reboot a browser that was healthy all along.
- **Preflight the bridge before an expensive per-item loop.** A batch that navigates once per item should assert connectivity first and bail out in seconds if it fails. Otherwise a bridge outage spends the entire batch's wall-clock budget producing one uniform failure row per item, which reads as "the site rejected everything" rather than "nothing ever connected."
- **Scope a metadata-repair sweep to the field that is actually broken.** A repair pass keyed on "author looks wrong" swept 47 notes, but only 8 had a numeric UID — the other 39 were hand-written notes with no author field at all. Match the exact broken shape (e.g. `author` is all digits), and fall back through every place the id can hide (frontmatter, then filename) before declaring a note unrepairable. Repair scripts must skip rather than guess: a note left untouched is recoverable, a note filled with a guess is not.
- **A stored "method X is blocked" conclusion goes stale on any browser restart.** Re-probe `Runtime.evaluate` / `Page.navigate` / in-page `fetch` on a fresh tab before telling the user a task needs their hands — refused navigation and dead API calls both get re-enabled by a restart or policy reload.
- **Never invent ports or paths — scan and fingerprint.** A `200` on a guessed path is usually an SPA catch-all; read status *and* content-type together. The front-end bundle is the API map for panels that ship no docs. Confirm a port serves what you assume — a port you assumed was the vendor panel may be the user's own side project.
- **A panel that bounces to `#/login/…` loads its privileged routes only after auth.** The bundle you can fetch while logged out holds just the public API surface; absence of a container/service endpoint proves nothing about whether one exists. See `references/cross-host-admin-grants.md` for the boundary sweep and the one-step handoff.
- **`location.hash` ending in `#/login/` is the verdict, not `localStorage`.** An `appKey` in storage is written before login finishes and reads like a live session.
- **Key material handed to a user must come from the private key.** A `known_hosts` line is indistinguishable from a public key and pastes cleanly while authorizing nothing.
- **`'Page.captureScreenshot' wasn't found` means wrong session, not a missing method.** Page/DOM
  domain commands have to ride the tab's attached session; `new_tab()` returns a **targetId**, and
  passing that as a session id fails with the same "method not found" wording.
  The **opposite** mistake is just as silent: after `Target.attachToTarget` (`flatten:true`) you must put
  the returned `sessionId` into **every** subsequent message body
  (`{"id":n,"method":…,"params":…,"sessionId":sid}`). Omit it and the call runs at browser level, so
  `Runtime.evaluate` returns no value and `document.querySelector(...)` reads `None` — which looks like
  "the page has no such element" while the real cause is "the message went to the wrong session".
  Self-check: after `Input.insertText`, read the field's `value.length` back — it must equal the number
  of characters you inserted; `None` means the sessionId is missing, not that the selector is wrong.
  Two neighbours in the same family: a WS handshake answering `403 Rejected an incoming WebSocket
  connection from the http://127.0.0.1:<port> origin` needs `suppress_origin=True` (or connect to the
  browser-level `/json/version` WS and attach from there), and `json.load(urlopen(...).read())` raises
  `AttributeError: 'bytes' object has no attribute 'read'` — decode first (`json.loads(...read().decode())`). In the bundled
  client the live session is `c._sid`: `c.call("Page.captureScreenshot", {"format": "png"}, c._sid)`.
  The reply is wrapped — the image is `r["result"]["data"]` (base64 PNG), not `r["data"]`; keying on
  the unwrapped shape reads as "capture failed" while the call actually succeeded. `Target.createTarget`
  replies `{"targetId": …}`: passing the whole result dict where a `targetId` is expected fails with
  `-32602 Invalid parameters … Failed to deserialize params.targetId - string value expected`.
  Let the page
  settle a few seconds after navigate, and sanity-check the file size: a blank page still returns
  a perfectly valid PNG.
- **`connect_over_cdp` `.pages` AttributeError**: pages are on `b.contexts[0]`, not the Browser.
- **`pkill -f "<localport>:127.0.0.1:<port>"` kills the shell that runs it.** The pattern matches the
  command line of the very invocation, so "restart the tunnel" ends the whole call (`exit -15`) and
  leaves the tunnel state unknown. Track the PID (`$!`) or use `-o ControlMaster`/`ControlPath` and
  `ssh -O exit`; or start the replacement on a fresh local port and let the stale one die on its own.
  Never wrap the tunnel itself in `timeout N`: it exits on schedule and every later call then fails with
  the same symptoms as a dead browser (`connection refused`, empty `/json/version`) while the browser is
  perfectly healthy. Run it as a long-lived background process with `ServerAliveInterval` instead, and
  treat "CDP went down mid-task" as "did my tunnel have a lifetime?" before touching the browser host.
- **Never steal the user's foreground.** The browser being driven is their daily driver, so every
  action has to be invisible to them: pass `background: true` when creating a target (the parameter
  has to be present at `Target.createTarget` time — activating afterwards does not undo the
  focus steal), never call `Page.bringToFront`, reuse one tab across a loop instead of opening one
  per item, and close only the tabs you opened. Keeping a helper's `activate_*_tab()` method
  raising unconditionally is a cheap way to make "just bring it up front" unrepresentable.
- **Playwright browser install location**: if the download fails with EACCES on a dirlock, the
  env var `PLAYWRIGHT_BROWSERS_PATH` points at a root-owned dir — override it to a writable path.
- **The bridge depends on the other host staying up.** State this as a constraint, not a bug.
- **Never type credentials.** Login walls are the user's to clear in their own window; the
  session is then reused over CDP without the secret ever entering the conversation.
- **A secret the page renders masked cannot be pulled out with the clipboard while you refuse focus.**
  `navigator.clipboard.readText()` throws `Document is not focused`, and focus emulation does not fix it
  (it can hang the CDP call). Read the value out of the page's own memory — storage plus React fiber
  `memoizedProps`/`memoizedState` — and write it straight to a 600 file without echoing it.
  Recipe: `references/in-page-secret-recovery.md`.
- **A rented cloud-browser session must be created and consumed inside one script.** Sessions expire
  between tool calls; reusing a saved `wsEndpoint` returns `404 {"code":"not_found","session not found"}`,
  which reads like a bad key. Probe plan capability with the minimal payload first — a `402` names the
  exact unsupported field (`useProxy`, `solveCaptchas`) — and prove the real egress country with an
  in-page `ipinfo.io/json` **before** judging whether the target site still blocks you.
  See `references/cloud-browser-sessions.md`.
- **Pin the endpoint — a shared helper's default may resolve to a different browser.** A helper that
  probes candidate ports can land on another Chromium on the same host, and then every answer
  ("what is my IP", "which tabs are open") describes the wrong machine: a country check reads `CN`
  while the user's browser really sits on a US node. Fingerprint it by comparing the `Browser` string
  from `/json/version` on the port you targeted against `navigator.userAgent` read in the page — a
  `Chrome/155` port serving a `Chrome/124` page is the wrong browser. Pass the endpoint explicitly.
- **`with <helper>():` closes the tab it created.** Bundled clients commonly call `Target.closeTarget`
  inside `close()`, which the context manager invokes on exit, so a `with` block that only opens and
  navigates leaves nothing behind for the next call. Run multi-call flows outside the context manager
  (or the whole flow inside it), and lean on the profile's cookie jar — a closed tab costs the tab,
  not the login.
- **A target created through `browser.new_browser_cdp_session().send("Target.createTarget")` never shows up in `ctx.pages`.** Playwright lists only the pages it auto-attached to, so the follow-up `for page in ctx.pages` loop finds nothing and the flow dies with "no page" while the tab is visibly open. Create the tab through the helper (`new_tab()` → targetId → `Target.attachToTarget`) or open it with a real URL and locate it by `page.url`, then drive that page with `connect_over_cdp`.
- **Multi-step form input: use playwright, not the raw request loop.** One long-lived playwright
  connection survives a relayed port; a hand-rolled id-matched loop meets `WebSocketTimeoutException`
  mid-sequence on the same link and you lose the half-filled form. Keep raw CDP for single probes and
  screenshots.
- **A React-controlled input ignores `el.value = …`.** Assigning the value plus dispatching
  `input`/`change` updates the DOM but not React state, so submit posts an empty field and the page
  simply does not advance — no error anywhere, which reads as "the button is dead". Use `page.fill()` /
  `page.type()`, or CDP `Input.insertText` after a real click on the field.
- **`role="presentation"` overlays swallow clicks.** Playwright reports `<div role="presentation">
  intercepts pointer events` and retries to timeout. `click(force=True)` or an in-page `.click()` gets
  through — read that message as "use force", not "element missing".
- **A localized UI makes English selectors match zero elements.** When the user's browser locale is
  Chinese, the button really is 「继续」/「设置」and `get_by_role(name="Continue")` returns count 0, which
  looks exactly like a missing control. Always try both languages (or a structural/positional selector)
  before concluding the page lacks the element.
- **Screenshot chain when a heavy SPA fights you.** `page.screenshot(clip=…)` can hang in "waiting for
  font"; take the full-page shot and crop with PIL instead. Raw `Page.captureScreenshot` over a relayed
  port frequently times out on the **first** attempt and succeeds on retry — wrap it in 3 attempts
  before reporting failure, and sanity-check file size (a blank page still yields a valid image).

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
- `references/cloud-browser-sessions.md` — renting a remote session (Hyperbrowser-style) to get an
  egress in another country: capability 402s, one-script lifetime, exit-IP proof, teardown, and the
  verification-code handoff that keeps the session alive while the user reads their inbox.
- `references/in-page-secret-recovery.md` — extracting a masked API key from a React page's fiber tree
  and storage when the clipboard path requires a focus you are not allowed to take.
