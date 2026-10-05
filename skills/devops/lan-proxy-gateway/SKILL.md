---
name: lan-proxy-gateway
description: Deploy and verify a LAN proxy gateway on a NAS/host.
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [proxy, mihomo, clash, sing-box, xray, nas, network, bandwidth, split-routing]
    related_skills: [remote-host-admin-escalation, remote-browser-cdp-bridge]
---

# LAN proxy gateway: deploy, verify, hand off

Task class: "give me a working 代理/梯子 for every device on my LAN, and make sure my
bandwidth is actually being used" — deployed on a NAS, a soft-router box, or a gateway host,
consumed by Windows/macOS/Linux/phone clients.

Covers clash/mihomo/sing-box/xray. The deliverable is **measured numbers plus a client config the
user can paste**, not a container that starts.

## When to Use

- The user asks for a 梯子 / 代理 / 科学上网 for the whole house, a LAN, or "所有设备都能用".
- A gateway container exists but must be switched to *their* subscription, or its nodes are stale.
- Someone claims "网速没跑满" / "宽带用不满" and you need measured proof of where the ceiling is.
- You are handed a Clash/mihomo/sing-box config to make correct and hand to non-technical clients.

## Procedure

1. **Inventory before installing.** List what already runs and whether it covers the
   requirement: `docker ps --format '{{.Names}}\t{{.Ports}}'`, then fingerprint each open port
   with a real request (status + content-type + title). An existing gateway may already be the
   right answer — or may be the wrong answer for one specific reason (e.g. it lacks the user's
   subscription). Report that distinction and let it decide; don't silently keep the incumbent or
   silently replace it.

2. **Ingest the subscription.** Airport endpoints gate on `User-Agent`; without a client UA you
   get `403` with a **misleading body** (it reads like a bad token, not a bad UA). Try
   `clash-verge/v1.6.0` / `clash.meta` / `mihomo/<ver>` and treat a body-only failure as a UA
   problem first. Never place the token in a script literal or command line — pass it through a
   variable that is unset at the end, and redact it from all output you echo back.

3. **Expect noise entries.** Subscriptions ship fake "proxies" for status text: remaining quota,
   days until reset, expiry date, "filtered N lines". They appear in node lists and poison health
   checks. Filter with a keyword regex before counting or reporting nodes.

4. **Write the config as: provider file + rules.** Keep node material in its own file
   (`proxy-providers` with `type: file`) and keep rules, DNS, and ports in the main config, so a
   subscription refresh is one file overwrite plus a restart.

5. **Validate with the binary, not your parser.** Run the image once with its config-test flag
   against a throwaway container and quote its verdict. Also confirm the rule database actually
   loaded (it prints a record count) — a config that parses can still match nothing.

6. **Verify auth and reachability separately.** `https://<blocked-host>` timing out before and
   returning `200` in a few hundred ms after is the proof that matters. Do not substitute "the page
   opened" or "a cookie exists".

7. **Measure bandwidth honestly** (see below — this is where reports usually go wrong).

8. **Hand off**: core address + one paste-block per client OS + the panel URL and key + how to
   refresh the subscription + a troubleshooting table. Write it into the user's vault next to the
   config so it survives the session.

## Measuring bandwidth without lying

- **A single-thread number is not a bandwidth number.** High-latency links cap out at single-digit
  Mbps regardless of capacity. Always measure with N parallel connections (start at 4, then 8/16 to
  find the ceiling) and report both: single-stream and parallel.
- **Validate the test URL before trusting a zero.** A `0 B/s` result usually means the source is
  blocked, the path doesn't support that transport (a QUIC/UDP-only node against a
  download-endpoint that needs TCP), or the file 404s — not that the link is slow. Probe with a
  small range request and check the status first.
- **Always run the no-proxy control against the identical URL.** Direct-vs-proxy on the same
  source is the only comparison that isolates the proxy from the source.
- **Report the link's own ceiling** from the NIC (`/sys/class/net/*/speed`) and the routing gateway
  (`ip route`). If the link negotiates at line rate but throughput tops out well below it, say so
  plainly — the bottleneck is upstream, not the hardware.
- Cross-check the proxy's measured ceiling against the plan's implied rate (quota ÷ days remaining
  × seconds). When they agree, the limit is on the provider side and no node swap will fix it.

## Client handoff, per OS

Give the mixed HTTP/SOCKS port once as the single address every client needs, then one paste-block
each:

- **Windows** — `$env:HTTP_PROXY`/`HTTPS_PROXY` for the current shell; `[Environment]::SetEnvironmentVariable(..., "User")` to persist; `git config --global http.proxy` and `npm config set proxy` for tools that ignore env vars. **Docker ignores env vars** — it needs daemon-level proxy config or explicit `-e` per container.
- **macOS / Linux** — `export http_proxy`/`https_proxy`, plus `all_proxy=socks5://…` when SOCKS is wanted; `pip config set global.proxy`, `npm config set proxy`.
- **Phone / tablet** — Clash/Shadowrocket profile with host + mixed port; device must be on the same LAN.

Include the panel URL + bearer key for live node switching, and note the mixed port is the only
address a client ever needs (DNS port is optional, for anti-pollution).

## Depth

- `references/mihomo-deployment.md` — known-good mihomo config skeleton (ports, fake-IP DNS,
  `proxy-providers` + rules split), the subscription-refresh command, and the API calls used for
  node health.

## Pitfalls

- **Node names break shell and URL handling.** Emoji + CJK + spaces survive `jq` but not
  `for n in $(...)` word-splitting, and they must be percent-encoded in REST paths — an encoded
  path returning `Resource not found` means your encoding, not a dead node. Iterate a newline file
  produced by `jq -r`, and read delays back from the group object's `history` rather than issuing
  one request per name.
- **A GUI-managed proxy rewrites its own config file.** Its panel keeps state in a database and
  regenerates `config.json` on every reload, reverting in-place edits on restart (a repeating
  `Quitting...` in the logs is the tell). Such a service must be changed through its own API —
  and if its credentials are unknown, say so and leave the file alone rather than guessing.
- **`type: file` providers ship status pseudo-nodes**; leaving them in a `url-test` group makes
  the selector flap onto an entry that cannot carry traffic.
- **Do not delete the incumbent's config.** Copy it aside with a dated suffix before any restart.
  A rollback that has no artifact is not a rollback.
- **Don't hand back a container that merely started.** Gate "done" on a cross-client reachability
  test plus measured throughput, then write the user-facing doc.
- **Long inline shell over SSH breaks silently** on quoting, and some remote shells are POSIX `sh`
  (function-declaration syntax is a parse error there). Base64-encode the payload and decode it on
  the far side; write loops, not `def f() { …; }`.
- **A local `execute_code` subprocess wrapper can reject extra kwargs** (e.g. a `bufsize` hook);
  when a one-off shell probe needs unusual flags, write it to a script file and run it with
  `terminal` instead of fighting the wrapper.
- **Write to a host-writable path, and chmod `600` any file holding node credentials.** Container
  bind mounts over a read-only or root-owned host tree fail in ways that look like permission
  errors on the wrong path.
- **Reach the gateway's management API for status, not SSH.** `GET /proxies` plus a
  `delay?url=…&timeout=…` call on the selector group gives real per-group health; the same call on
  a raw node name needs exact encoding and returns nothing useful when it is wrong.
