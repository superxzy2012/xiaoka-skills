---
name: proxy-split-routing-ops
description: Use when deploying or repairing proxy routing on a host.
version: 1.0.0
author: Hermes (curator)
license: MIT
metadata:
  hermes:
    tags: [proxy, mihomo, clash, v2raya, routing, nas, docker, network]
    related_skills: [remote-host-admin-escalation, remote-browser-cdp-bridge]
---

# Proxy & split-routing ops on a self-hosted host

Deploy or repair a proxy gateway on a machine you administer (NAS, mini PC, VPS), and prove that
domestic traffic stays direct while foreign traffic is proxied.

Use when: a host is slow to GitHub / Docker Hub / npm, a user wants a subscription configured,
a proxy container is running but using the wrong nodes, or routing must split by destination.

## Rule

**Inventory before installing.** A host that looks like it "needs a proxy" usually already has
one running — with the wrong subscription, no subscription, or an unreachable upstream.
`docker ps` first. Adding a second gateway beside the first produces two exit IPs and no way for
the user to tell which one a client is using, and the new one silently wins for whichever env
var happens to point at it.

## Procedure

1. **Inventory what already runs, and what it already reaches.**
   ```bash
   docker ps --format '{{.Names}} | {{.Image}} | {{.Ports}}'
   docker ps -a --format '{{.Names}} | {{.Status}}' | grep -iE 'mihomo|clash|v2ray|sing|openclash'
   docker inspect <name> --format '{{.HostConfig.NetworkMode}}'
   docker inspect <name> --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'
   ```
   For each candidate, read its real inbound ports from *inside* the container
   (`netstat -tlnp`), never from documentation or the image's usual port. Read its current
   upstream node names and count. If it already serves traffic, your job is usually to
   **repoint its upstream**, not to add a gateway.

2. **Measure a direct-connect baseline per destination class, before changing anything.**
   Probe one URL per class — domestic mirror, overseas site, the registry/CDN the user complains
   about — and record ms + status. A class that times out directly is the class that needs the
   proxy; a class already fast must stay direct or you make it worse.
   ```bash
   for u in https://github.com https://registry-1.docker.io/v2/ https://mirrors.aliyun.com; do
     curl -s -o /dev/null -w "$u %{time_total}s http=%{http_code}\n" -m 12 "$u"
   done
   ```
   Re-measure rather than trusting a stored conclusion: "Docker Hub times out" is often stale, and
   a daemon may reach a registry its own host cannot curl directly.

3. **Ingest the subscription, then let the software validate it.**
   Fetch with a client User-Agent (`curl -A 'clash-verge/v1.6.0'`) — airport panels 403 a default
   curl. Keep the raw provider file separate from your main config and reference it via
   `proxy-providers: {type: file}`. Then run the binary's own test mode and quote its verdict:
   ```bash
   docker run --rm -v <dir>:/root/.config/mihomo <image> -t -d /root/.config/mihomo
   # -> "configuration file ... test is successful", or it names the offending line
   ```
   Grepping YAML for `- name:` returns `0` on inline `{ name: ... }` blocks and tells you
   nothing; the binary's parser is the only trustworthy counter.

4. **Start it network-host with a restart policy, then confirm the ports.**
   ```bash
   docker run -d --name mihomo --restart unless-stopped --network host \
     -v <dir>:/root/.config/mihomo <image>
   ```
   `NetworkMode: host` serves the LAN without publishing ports. Verify each port answers from the
   host, then grep the startup log for `error|failed` — an empty result is the pass.

5. **Verify split routing through one port, by latency class.**
   Send every class through the proxy's own mixed port and compare against step 2. Domestic
   targets holding baseline speed are hitting `DIRECT`; a previously-dead overseas target now
   returning 200 in hundreds of ms is hitting the proxy. This proves the *rules* fire, not just
   that a socket opens.

6. **Verify the exit IP, per client port.** Query an IP-echo endpoint
   (`ip-api.com/json?fields=query,country,isp`) through each port you expose. Two ports
   returning different countries means one is still on the old upstream — **HTTP 200 proves a
   proxy exists, never which node it is.** This is the only check that catches a half-applied
   config.

## Pitfalls

- **`HTTP 200` is not proof of routing.** Every proxied request returns 200 whether it went
  through the intended node or a leftover default. Compare exit IPs, not status codes.
- **A management panel regenerates the config file it owns.** v2rayA persists to its own database
  and rewrites `config.json` from it on every reload, so `docker cp` + restart silently reverts —
  no error anywhere, and repeated `Quitting…` in the log is the tell. Write through the panel's
  HTTP API or not at all; confirm any file write survived a restart with `md5sum` before and after.
- **Assume the panel's documented port is wrong.** Read the listener from inside the container. A
  host-network panel on `3017` while every doc and guess says `2017` costs an afternoon.
- **Bind-mounted config paths are host paths.** The file that survives a container recreate is the
  mount *source* on the host; a file written only inside the container is a copy a `create` discards.
- **`ssh host 'cmd'` does not export local env vars to the remote shell.** Passing
  `env={"TOKEN": ...}` to `subprocess` yields `token is null` from the remote service while the
  script looks correct. Export the secret *inside* the remote script and scrub it from captured
  output — see `references/credentials-over-remote-shell.md`.
- **Never guess a panel password.** A `401` on a health endpoint means ask the user for the
  credentials or have them import the subscription in the UI. An unauthenticated `404` proves
  nothing — privileged routes are absent from the bundle a logged-out fetch returns.
- **Add a new outbound rather than rewriting existing ones.** Insert the new upstream, repoint
  the routing rules at it explicitly (rules whose `outboundTag` is `null` fall through to
  whichever outbound is first), verify by exit IP, then remove the old one.
- **Changing the host gateway's upstream changes the exit IP for every device behind it**, and
  clients resolving split DNS separately may bypass it entirely. Say who is affected first.
- **Check disk before pulling images.** A NAS at 82% with 3.3G free fails mid-pull, and the
  partial layer is not cleaned up by a retry.

## Depth

- `references/credentials-over-remote-shell.md` — getting a secret to a far-side shell without
  leaking it to `argv`, `ps`, or the transcript; telling a delivery bug apart from a bad credential.
- `references/panel-owned-configs.md` — panels that rewrite their own config, and the read/verify
  loop that distinguishes "reverted by the panel" from "never written".
