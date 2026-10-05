# Panels that own their config file

Read this when a proxy/gateway service is fronted by a management panel and your config edit
appears to have done nothing.

## Why the edit vanishes

The panel holds its state in its own database and **regenerates the config file from that database
on every reload**. The file you edited is a derived artifact. `docker cp`, a host-side write, and a
service restart all look successful; on reload the panel rewrites the file from its DB and your
change is gone with no error in any log.

Tells, in order of reliability:

1. **The file reverted byte-for-byte.** `md5sum` before your write, after your write, and after a
   restart. If step 2 matches step 1, the panel overwrote you — you now know it was never a
   syntax or ordering problem.
2. **The service log repeats `Quitting…`.** A config the core rejects on load restarts in a loop.
   This also means your JSON/YAML parsed and the *semantics* were rejected — read the error above
   the repeated line.
3. **The container's file mtime is older than your write.** You wrote a copy the panel never read.

## What to do

- **Use the panel's HTTP API.** It is the only supported write path for a panel-owned config. Find
  it by fingerprinting the panel's real port (see below), then read the front-end bundle for the
  route list — but only the routes a *logged-in* fetch exposes.
- **Never guess a panel password.** A `401` on the health/touch endpoint means you need the user's
  credentials. Hand them the URL and the exact UI path (Settings → Subscription → Add) and stop.
  An unauthenticated `404` proves nothing either way, so do not conclude "no such endpoint".
- **When no panel owns the file** (a bare mihomo/clash with a static config), edit the file
  directly and verify with `md5sum` after a restart.

## Finding the real port

A service on `NetworkMode: host` advertises its *documented* port in your head while binding
another. Read the ground truth:

```bash
sudo -n docker inspect <name> --format '{{.HostConfig.NetworkMode}}'
sudo -n docker exec <name> sh -c 'netstat -tlnp 2>/dev/null || ss -tlnp'
```

Then fingerprint each candidate by content, not by port number — a `200 text/html` with
`<title>Sun-Panel</title>` is someone's dashboard, and `<title>Gitea…</title>` is a forge. Reading
the title is what stops you from building on the wrong service.

## Repointing without breaking the user

When the goal is "use my subscription instead of the current nodes":

1. **Add** a new outbound pointing at the new upstream; leave existing outbounds untouched.
2. **Repoint routing explicitly.** Rules with `"outboundTag": null` fall through to whichever
   outbound is first in the array — they are not "unrouted". Set them by name.
3. **Leave inbounds alone.** Transparent-proxy / dokodemo-door / TProxy inbounds encode the user's
   LAN setup; rewriting them silently breaks interception for every device.
4. **Verify by exit IP**, per client port, before removing anything.
5. **Back up the original config inside the container** before the first edit, and say where the
   backup lives so rollback is one command.

## What "verified" means here

Not: the service restarted without error, the JSON parsed, the port answers.
Yes: a request through the client port returns the **new** upstream's country and IP, and the
user's transparent-proxy inbounds are still listed.
