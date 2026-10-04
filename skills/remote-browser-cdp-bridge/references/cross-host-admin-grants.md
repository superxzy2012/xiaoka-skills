# Getting admin on a host you only share a browser with

Read this when a task needs real privileges on another machine (install a container, edit system
config, open a port) and you currently have none. The goal is to get to the *first* action that
needs credentials, then hand off — not to keep probing.

## Establish the permission boundary in one sweep, then stop

Probe every channel once, in a single pass, and record the result. Do not keep re-probing
across turns while the answer is the same.

| Channel | Probe | Meaning when it fails |
|---|---|---|
| SSH to the target | `ssh -i <key> -o BatchMode=yes <user>@<host> 'id'` over the plausible usernames | port open + `Permission denied` = you need the user to authorize you |
| Shared filesystem write | `touch <mount>/.wtest && rm <mount>/.wtest` | read-only mount = you cannot deploy anything there |
| Vendor control panel API | fingerprint the panel's real port (see below), then look for a container/service endpoint | unauthenticated 404 = needs panel credentials |
| Docker socket / data dir | `ls <mount>/@docker/containers` | `Permission denied` = no deploy path from here |
| Browser CDP | see `remote-browser-cdp-bridge` | useful for *reading*, not for privileged writes |

Then state the boundary plainly: which operations are impossible from here, and why. "I am in a
restricted uid and cannot write outside the mounted subtree" is a real answer; a fifth identical
`Permission denied` is not.

## Panel ports: never guess, fingerprint

A `200` on a guessed API path is usually the SPA catch-all, not an endpoint. Read **status and
content-type together** — `200 text/html` on every path means you are hitting the router.

Scan the likely ports once, then identify each open port by what it actually serves:

```bash
for p in 22 80 443 3000 5000 5001 6789 8000 8080 8443 9000 9090 2375 2376 9999; do
  timeout 3 bash -c "exec 3<>/dev/tcp/$HOST/$p" 2>/dev/null && echo "$p open"
done
curl -si -m 8 "http://$HOST:$PORT/" | head -12   # headers fingerprint the service
```

Headers that identify services: a `Location: /...?os=<name>` redirect names the vendor OS; a
`Www-Authenticate: Basic realm="Restricted"` means an API needing credentials; a
`Set-Cookie: i_like_gitea=` means that port is something unrelated entirely.

**A port you assumed is your own app may belong to something the user runs.** Confirm what a
port serves before building on it — assuming a port is the vendor panel and it is actually the
user's side project sends the whole task down the wrong path.

## The one-step authorization handoff

When the only thing standing between you and the task is credentials, hand back the *shortest
possible* privileged command and nothing else. No config to review, no paths to choose, no
second step. The user should paste one block and be done.

Target shape: create the key dir, append the pubkey, fix perms, print a confirmation count.

### Deriving the pubkey — never hand-copy it

`ssh-keygen -y -f <private>` output **already carries the comment field**. Concatenating a
comment onto it again yields `xiaoka@nas xiaoka@nas`, which SSH rejects while exiting 0 — the
handoff silently authorizes nothing and the failure surfaces later as a bare
`Permission denied`. Use the `ssh-keygen -y` output verbatim.

A `known_hosts` line pastes just as cleanly and authorizes nothing at all, because that key
belongs to whatever host fingerprinted last. Only the private key is a source of truth.

### Ship the handoff only after executing it

Before the user ever sees the command:

1. `bash -n` the block (syntax).
2. Run it with `HOME=$(mktemp -d)` so it writes into a throwaway dir — never touch a real `~/.ssh`.
3. `ssh-keygen -lf` the produced `authorized_keys` **and** the private key; compare fingerprints.
4. Assert the comment appears exactly once.

Steps 2–4 are what catch the duplicate-comment and truncated-key bugs. A syntactically valid
command is not a correct one.

### Scope the grant to the least privilege that works

Name the narrow group that suffices (e.g. the container runtime group) instead of root. If the
user's account already has it, the grant is a no-op and the task proceeds. Say how to revoke:
delete that one line from `authorized_keys`.

## State the blocker as a blocker

When the boundary is real, say the task is not done and name the exact permission missing.
Offering a config file or a script the user must run themselves is fine — presenting it as
*done* is not. Do not describe prepared work as a completed install.